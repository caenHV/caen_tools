"""HealthControl: performs continuous quality check 
of current parameters on CAEN device
"""

from functools import reduce

import logging
import timeit

from caen_tools.SystemCheck.scripts.failure_actions import (
    check_and_increase,
    check_and_restart,
    failure_actions,
    reduce_voltage,
)
from caen_tools.SystemCheck.utils.structures import (
    ChannelStatus,
    CheckStatus,
    HealthControlSettings,
    RampDownInfo,
    ErrorCode,
    CheckResult,
    Codes,
)

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError
from caen_tools.SystemCheck.utils.counter import CounterTTL

from .metascript import Script
from .mchswork import MChSWorker
from .receipts import Services, PreparedReceipts


class HealthControl(Script):
    """Class to performs checks of the devback parameters"""

    SENDER = "syscheck/healthcontrol"
    MCHS_KEY = "healthok"

    def __init__(
        self,
        settings: HealthControlSettings,
        mchs: MChSWorker,
        stop_on_failure: list[Script] | None = None,
    ):
        super().__init__(shared_parameters=settings.shared_parameters)
        self.cli = AsyncClient(
            {
                Services.MONITOR: settings.monitor,
                Services.DEVBACK: settings.devback,
                Services.CHECK: settings.check,
            }
        )
        self.mchs = mchs
        self.dependent_scripts = stop_on_failure if stop_on_failure is not None else []
        self._low_voltage_mlt: float = settings.low_voltage_mlt
        self.__max_currents: dict[str, dict[str, float | dict[str, float]]] = (
            settings.max_currents
        )
        self._rdown_info: dict[str, RampDownInfo] = settings.ramp_down_trip_time
        self._allowed_down_window: float = settings.allowed_down_window
        self._breakdown_time_window: float = settings.breakdown_time_window

        # Setup Time expiring counters for emergency downs and electrical breakdowns.
        self._num_downs = CounterTTL(self._allowed_down_window)
        self._num_breakdowns = CounterTTL(self._breakdown_time_window)

        self._n_allowed_downs: int = settings.n_allowed_downs
        self._auto_restart_after: float = settings.auto_restart_after
        self._reduce_period: float = settings.reduce_period
        self._soft_reduce_mod: float = settings.soft_reduce_mod

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

        cur_voltage_mlt: float = reduce(
            lambda x, y: x + y["VSet"], pars.values(), 0
        ) / reduce(lambda x, y: x + y["VDef"], pars.values(), 0)

        logging.debug(
            "Is low voltage defined: %s (%.3f, %.3f)",
            cur_voltage_mlt <= self._low_voltage_mlt,
            cur_voltage_mlt,
            self._low_voltage_mlt,
        )
        return cur_voltage_mlt <= self._low_voltage_mlt

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
                case ChannelStatus(
                    ramp_down=True, voltage_problems=True
                ) | ChannelStatus(ramp_down=True, soft_current_limit=True):
                    ch_statuses[ch] = self._rdown_info[ch].check_trip_time()
                    if not ch_statuses[ch]:
                        logging.warning(f"Channel {ch} exceeded trip time.")
                case ChannelStatus(voltage_problems=True) | ChannelStatus(
                    soft_current_limit=True
                ):
                    logging.warning(
                        f"Channel {ch} is not in a ramp down but is in either over/under voltage or over current. It is on its last breath trip time."
                    )
                    ch_statuses[ch] = self._rdown_info[ch].check_trip_time()
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

        match status.failure:
            case (ErrorCode.SOFT_OVERCURRENT, _):
                await reduce_voltage(self, status)
            case (err, _) if isinstance(err, ErrorCode):
                await failure_actions(self, status)
            case _:
                self.send_mchs(status.ack)

        if self.shared_parameters["auto_restart"]:
            await check_and_restart(self)
            await check_and_increase(self)

        exectime = timeit.default_timer() - starttime
        logging.info("HealthControl was done in %.3f s", exectime)
        return
