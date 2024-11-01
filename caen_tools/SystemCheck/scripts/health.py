"""HealthControl: performs continuous quality check 
of current parameters on CAEN device
"""

from functools import reduce

import logging
import time
import timeit

from caen_tools.SystemCheck.utils.structures import (
    Address,
    ChannelStatus,
    CheckStatus,
    RampDownInfo,
    ErrorCode,
    ErrorDescription,
    HealthParametersDict,
    CheckResult,
    Codes,
)

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError

from .metascript import Script
from .mchswork import MChSWorker
from .receipts import Services, PreparedReceipts


class HealthControl(Script):
    """Class to performs checks of the devback parameters"""

    SENDER = "syscheck/healthcontrol"
    MCHS_KEY = "healthok"

    def __init__(
        self,
        shared_parameters: HealthParametersDict,
        devback: Address,
        monitor: Address,
        check: Address,
        mchs: MChSWorker,
        max_currents: dict[str, dict[str, float]],
        ramp_down_trip_time: dict[str, RampDownInfo],
        stop_on_failure: list[Script] | None = None,
    ):
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient(
            {
                Services.MONITOR: monitor,
                Services.DEVBACK: devback,
                Services.CHECK: check,
            }
        )
        self.mchs = mchs
        self.dependent_scripts = stop_on_failure if stop_on_failure is not None else []
        self.__max_currents: dict[str, dict[str, float]] = max_currents
        self.__rdown_info: dict[str, RampDownInfo] = ramp_down_trip_time

    async def on_stop(self):
        self.mchs.pop_keystate(self.MCHS_KEY)

    def form_answer(self, code: Codes) -> None:
        self.shared_parameters["last_check"] = CheckResult(code)
        return

    def _check_ramping(self, pars: dict) -> bool:
        """Checks that channels are not in ramp up/down state."""

        def is_ramping_status(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1]
            return st[1] == "1" or st[2] == "1"

        is_ramping = False
        try:
            is_ramping = any(
                [is_ramping_status(val["ChStatus"]) for val in pars.values()]
            )
        except KeyError as e:
            logging.warning("RampGuard could not access ChStatus: %s", e)

        if is_ramping:
            logging.info("Ramping status detected")

        return is_ramping

    def _check_lowvolt(self, pars: dict) -> bool:
        """Checks if current defined voltage multiplier level is lower of a limit"""

        low_voltage_mlt: float = self.shared_parameters["low_voltage_mlt"]
        cur_voltage_mlt: float = reduce(
            lambda x, y: x + y["VSet"], pars.values(), 0
        ) / reduce(lambda x, y: x + y["VDef"], pars.values(), 0)

        logging.debug(
            "Is low voltage defined: %s (%.3f, %.3f)",
            cur_voltage_mlt <= low_voltage_mlt,
            cur_voltage_mlt,
            low_voltage_mlt,
        )
        return cur_voltage_mlt <= low_voltage_mlt

    def _overall_checks(
        self, pars: dict
    ) -> tuple[dict[str, ChannelStatus] | None, dict[str, ChannelStatus]]:
        imon_key = lambda value: "IMonH" if value["ImonRange"] == 0 else "IMonL"
        statuses: dict[str, ChannelStatus] = {}
        try:
            for ch, val in pars.items():
                statuses[ch] = ChannelStatus.form(
                    val["ChStatus"], val[imon_key(val)], self.__max_currents[ch]
                )
            bad_channels = {
                ch: status for ch, status in statuses.items() if status.is_bad
            }
        except Exception as e:
            bad_channels = None
            logging.warning("Something went wrong during channel check: %s", e)
        return bad_channels, statuses

    def _apply_trip_time_premium(
        self,
        bad_channels: dict[str, ChannelStatus],
    ):
        ch_statuses = {}
        for ch, status in bad_channels.items():
            match status:
                case ChannelStatus(bad_status=True) | ChannelStatus(
                    current_problems=True
                ):
                    ch_statuses[ch] = False
                case ChannelStatus(ramp_down=True, voltage_problems=True):
                    # Trip time logic is here
                    ch_statuses[ch] = self.__rdown_info[ch].check_trip_time()
                    if not ch_statuses[ch]:
                        logging.warning(f"Channel {ch} exceeded trip time.")
                case ChannelStatus(voltage_problems=True):
                    logging.warning(
                        f"Channel {ch} is not in a ramp down but is in either over/under voltage or over current. It is on its last breath trip time."
                    )
                    ch_statuses[ch] = self.__rdown_info[ch].check_trip_time()
        try:
            bad_channels_errs = {
                ch: ErrorCode.from_ChannelStatus(status)
                for ch, status in bad_channels.items()
                if not ch_statuses[ch]
            }

            overall_error = None
            error_description = ""
            if len(bad_channels_errs) > 0:
                overall_error = reduce(
                    lambda val, sum: val | sum, bad_channels_errs.values()
                )
                if len(overall_error) > 1:
                    overall_error = ErrorCode.MULTIPLE

                error_description = f"There are following problems {[f'Channel {ch}: {err_code}' for ch, err_code in bad_channels.items()]}. Overall status is {overall_error}."
        except Exception as e:
            overall_error = ErrorCode.CANT_READ
            logging.warning(
                "Something went wrong while the trip time criteria had been checked: %s",
                e,
            )
            error_description = (
                f"Something went wrong while the trip time criteria had been checked."
            )
        return overall_error, error_description

    def perform_checks(self, params_dict: dict) -> CheckStatus:
        """All checks of the recieved parameters are here"""

        logging.debug("Perform parameters check: %s", params_dict)

        bad_channels, all_statuses = self._overall_checks(params_dict)
        if bad_channels is None:
            error_code = ErrorCode.CANT_READ
            status_description = "Something went wrong during channel check."
        else:
            error_code, status_description = self._apply_trip_time_premium(bad_channels)

        is_ramping = any([status.is_ramping for _, status in all_statuses.items()])
        if is_ramping:
            logging.info("Ramping status detected")
        is_lowvolt = self._check_lowvolt(params_dict)

        good_device = error_code is None
        unstable_params = is_ramping or is_lowvolt

        if good_device and not unstable_params:
            return CheckStatus(ack=True)
        elif good_device and unstable_params:
            return CheckStatus(ack=False)

        logging.warning(
            "Device is not ok: error = %s, description = %s",
            error_code,
            status_description,
        )
        return CheckStatus(ack=False, failure=(error_code, status_description))  # type: ignore

    def send_mchs(self, status: bool) -> None:
        """Sends ACK (True) or NACK (False) on MChS"""
        self.mchs.set_state(**{self.MCHS_KEY: status})
        self.mchs.send_state()
        return

    async def failure_actions(self, status: CheckStatus) -> None:
        """A number of actions on failure"""

        logging.error("Bad device parameters. Emergency DownVoltage!")

        for script in self.dependent_scripts:
            script.stop()

        # Send bad news on mchs
        self.send_mchs(False)

        logging.debug("Send Down Voltage Receipt")
        down_voltage = await self.cli.query(PreparedReceipts.down(self.SENDER))
        logging.info(
            "Send emergency status of the device: is_ok = %s, description = %s",
            False,
            status.failure[1],  # type: ignore
        )

        if isinstance(down_voltage.response, ReceiptResponseError):
            logging.error(
                "Not sent DownVoltage Receipt (%s)! Try again...", down_voltage.response
            )
            down_voltage = await self.cli.query(PreparedReceipts.down(self.SENDER))
            logging.info("Final response (%s)", down_voltage.response)

        self.shared_parameters["last_down"] = time.time()
        await self.cli.query(
            PreparedReceipts.sendlog(
                self.SENDER,
                (
                    f"{status.failure[0]}: {status.failure[1]}"
                    if status is not None
                    else "Down voltage due to bad device params (generic error)"
                ),
                True,
            ),
            receive_time=0.5,
        )

        return

    async def check_and_restart(self):
        end_time = time.time()
        start_time = end_time - self.shared_parameters["allowed_down_window"]
        get_n_downs = await self.cli.query(
            PreparedReceipts.get_last_downs(
                self.SENDER, start_time=int(start_time), end_time=int(end_time)
            )
        )
        if isinstance(get_n_downs.response, ReceiptResponseError):
            logging.warning("Error from Monitor %s", get_n_downs.response)
            self.form_answer(Codes.MONITOR_ERROR)
            self.shared_parameters["last_down"] = None
            self.shared_parameters["auto_restart"] = False
            return

        n_consecutive_downs = None
        if get_n_downs.response.statuscode == 1:
            n_consecutive_downs = int(get_n_downs.response.body)

        if (
            n_consecutive_downs is None
            or n_consecutive_downs > self.shared_parameters["n_allowed_downs"]
        ):
            self.shared_parameters["last_down"] = None
            self.shared_parameters["auto_restart"] = False
            logging.warning(
                "Too many emergency downs (%s) in last %s seconds. Autopilot will not be restarted.",
                n_consecutive_downs,
                self.shared_parameters["allowed_down_window"],
            )
            return

        logging.debug(f"Last down timestamp is = {self.shared_parameters["last_down"]}, autorestart time = {self.shared_parameters["auto_restart_after"]}")
        if (
            self.shared_parameters["last_down"] is not None
            and time.time() - self.shared_parameters["last_down"]
            < self.shared_parameters["auto_restart_after"]
        ):
            self.shared_parameters["last_down"] = None
            autopilot_status = await self.cli.query(
                PreparedReceipts.get_autopilot_params(self.SENDER), 1
            )
            if isinstance(autopilot_status.response, ReceiptResponseError):
                logging.warning(
                    "Problem with autopilot status %s", autopilot_status.response
                )
                return
            target_voltage = autopilot_status.response.body["autopilot"].get(
                "target_voltage", None
            )
            logging.info(f"target_voltage = {target_voltage}")

            if target_voltage is not None:
                autopilot_restart = await self.cli.query(
                    PreparedReceipts.set_autopilot(self.SENDER, True, target_voltage), 1
                )
                if isinstance(autopilot_restart.response, ReceiptResponseError):
                    logging.warning(
                        "Problem with autopilot start %s", autopilot_restart.response
                    )
                    return
                logging.info(
                    "Autopilot was restarted after emergency down with target voltage = %s",
                    target_voltage,
                )

    async def __send_system_status(self):
        autopilot_status = await self.cli.query(
            PreparedReceipts.get_status_autopilot(self.SENDER)
        )
        if isinstance(autopilot_status.response, ReceiptResponseError):
            logging.warning(
                "Problem with autopilot status %s", autopilot_status.response
            )
            return

        autoplt_stat_val = autopilot_status.response.body["interlock_follow"]
        await self.cli.query(
            PreparedReceipts.writedict_odb(
                self.SENDER,
                dict(
                    AUTOPILOT=int(autoplt_stat_val),
                ),
            )
        )
        return

    async def exec_function(self):
        """Logic:
        1. Get parameters from CAEN device
        2. Perform some checks
          If Checks OK -> send ACK on mchs
          If Checks FAILED ->
            send NACK on mchs
            down voltage on setup
            turn off specified scripts
            set last_down time
        3. If enough time elapsed restarts dependent scripts (if auto_restart is on)

        """
        logging.debug("Start HealthControl script")
        starttime = timeit.default_timer()

        await self.__send_system_status()

        devback_params = await self.cli.query(
            PreparedReceipts.get_params(
                self.SENDER, ["IMonH", "IMonL", "ImonRange", "ChStatus", "VSet", "VDef"]
            )
        )
        if isinstance(devback_params.response, ReceiptResponseError):
            logging.warning("Error from DeviceBackend %s", devback_params.response)
            self.form_answer(Codes.DEVBACK_ERROR)
            return

        params_dict = devback_params.response.body["params"]
        status: CheckStatus = self.perform_checks(params_dict)

        if status.failure is not None:
            await self.failure_actions(status)
        else:
            self.send_mchs(status.ack)

        if self.shared_parameters["auto_restart"]:
            await self.check_and_restart()

        exectime = timeit.default_timer() - starttime
        logging.info("HealthControl was done in %.3f s", exectime)
        return
