"""HealthControl: performs continuous quality check 
of current parameters on CAEN device
"""

from enum import IntEnum
from functools import reduce
from typing import TypeAlias

import logging
import time
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError

from .metascript import Script
from .mchswork import MChSWorker
from .structures import HealthParametersDict, CheckResult, Codes
from .receipts import Services, PreparedReceipts
from ..utils import RampDownInfo

Address: TypeAlias = str


class CheckStatus(IntEnum):
    """Statues of the performed check"""

    ACK = 1
    NACK = 2
    FAILURE = 3


class HealthControl(Script):
    """Class to performs checks of the devback parameters"""

    SENDER = "syscheck/healthcontrol"
    MCHS_KEY = "healthok"

    def __init__(
        self,
        shared_parameters: HealthParametersDict,
        devback: Address,
        monitor: Address,
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
        cur_voltage_mlt: float = reduce(lambda x, y: x + y["VSet"], pars.values(), 0) / reduce(
            lambda x, y: x + y["VDef"], pars.values(), 0
        )

        logging.debug(
            "Is low voltage defined: %s (%.3f, %.3f)",
            cur_voltage_mlt <= low_voltage_mlt,
            cur_voltage_mlt,
            low_voltage_mlt,
        )
        return cur_voltage_mlt <= low_voltage_mlt

    def __check_ch_status(self, pars: dict) -> bool:
        """Check channels statuses.

        Parameters
        ----------
        pars : dict
            channel parameters

        Returns
        -------
        tuple[bool, bool]
            (is_status_ok, is_only_overvoltage)
        """

        def good_status(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1][3:13]
            return int(st) == 0

        def is_only_over_under_voltage(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1][3:13]
            is_good = int(st) == 0
            is_only_overvoltage = (
                (st[1] == "1" or st[2] == "1") and st[0] == "0" and int(st[3:]) == 0
            )
            return is_only_overvoltage

        def is_rdown_status(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1]
            return st[2] == "1"

        def check_time(info: RampDownInfo) -> bool:
            """If is_rdown time exceeds trip_time returns False, otherwise returns True."""
            if info.timestamp is None:
                return True
            return time.time() - info.timestamp < info.trip_time

        status = False
        bad_channels = []
        only_over_under_volt_channels = []
        ch_statuses = dict()
        try:
            for ch, val in pars.items():
                ch_statuses[ch] = good_status(val["ChStatus"])
                if not ch_statuses[ch]:
                    bad_channels.append(ch)
                if not ch_statuses[ch] and is_only_over_under_voltage(val["ChStatus"]):
                    only_over_under_volt_channels.append(ch)

                    if self.__rdown_info[ch].timestamp is None and is_rdown_status(
                        val["ChStatus"]
                    ):
                        self.__rdown_info[ch].timestamp = time.time()
                        self.__rdown_info[ch].last_breath = False
                        self.__rdown_info[ch].is_rdown = True

                    if is_rdown_status(val["ChStatus"]):
                        if check_time(self.__rdown_info[ch]):
                            ch_statuses[ch] = True
                        else:
                            logging.warning(f"Channel {ch} exceeded trip time.")
                        continue

                    if self.__rdown_info[ch].last_breath:
                        if not check_time(self.__rdown_info[ch]):
                            ch_statuses[ch] = False
                            self.__rdown_info[ch].reset()
                            logging.warning(f"Channel {ch} exceeded trip time.")
                        else:
                            ch_statuses[ch] = True
                    else:
                        self.__rdown_info[ch].is_rdown = False
                        self.__rdown_info[ch].last_breath = True
                        self.__rdown_info[ch].timestamp = time.time()
                        ch_statuses[ch] = True
                        logging.warning(
                            f"Channel {ch} is not in a ramp down but is in over/under voltage. It receives last breath trip time."
                        )

                self.__rdown_info[ch].last_breath = False
                self.__rdown_info[ch].timestamp = None

            status = all(ch_statuses.values())
        except Exception as e:
            logging.warning("Can't check channels status. %s", e)

        if not status:
            logging.warning(
                f"Channels {bad_channels} statuses are bad. Channels {only_over_under_volt_channels} are in over/under voltage."
            )
        return status

    def __check_currents(self, pars: dict) -> bool:
        def max_current_key(ch_status: str) -> str:
            st = format(int(ch_status), "015b")[::-1][:13]
            key = "volt_change" if int(st[1]) == 1 or int(st[2]) == 1 else "steady"
            return key

        imon_key = lambda value: "IMonH" if value["ImonRange"] == 0 else "IMonL"

        status = False
        currents_status = {}
        try:
            currents_status = {
                ch: val[imon_key(val)]
                < self.__max_currents[ch][max_current_key(val["ChStatus"])]
                for ch, val in pars.items()
            }
            status = all(currents_status.values())
        except KeyError as e:
            logging.warning("Can't find channel max current in config: %s", e)
            status = False

        if not status:
            logging.warning(
                f"Channels {[ch for ch, stat in currents_status.items() if not stat]} currents are bad."
            )
        return status

    def perform_checks(self, params_dict: dict) -> CheckStatus:
        """All checks of the recieved parameters are here"""

        logging.debug("Perform parameters check: %s", params_dict)

        is_status_ok = self.__check_ch_status(params_dict)
        is_current_ok = self.__check_currents(params_dict)
        is_ramping = self._check_ramping(params_dict)
        is_lowvolt = self._check_lowvolt(params_dict)

        good_device = is_status_ok and is_current_ok
        unstable_params = is_ramping or is_lowvolt

        if good_device and not unstable_params:
            return CheckStatus.ACK
        elif good_device and unstable_params:
            return CheckStatus.NACK

        logging.warning("Bad parameters found: %s", params_dict)
        return CheckStatus.FAILURE

    def send_mchs(self, status: bool) -> None:
        """Sends ACK (True) or NACK (False) on MChS"""
        self.mchs.set_state(**{self.MCHS_KEY: status})
        self.mchs.send_state()
        return

    async def failure_actions(self) -> None:
        """A number of actions on failure"""

        logging.error("Bad deivce parameters. Emergency DownVoltage!")

        for script in self.dependent_scripts:
            script.stop()

        # Send bad news on mchs
        self.send_mchs(False)

        logging.debug("Send Down Voltage Receipt")
        down_voltage = await self.cli.query(PreparedReceipts.down(self.SENDER))
        if isinstance(down_voltage.response, ReceiptResponseError):
            logging.error(
                "Not sent DownVoltage Receipt (%s)! Try again...", down_voltage.response
            )
            down_voltage = await self.cli.query(PreparedReceipts.down(self.SENDER))
            logging.info("Final response (%s)", down_voltage.response)
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
        """
        logging.debug("Start HealthControl script")
        starttime = timeit.default_timer()

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

        match status:
            case CheckStatus.FAILURE:
                await self.failure_actions()
            case CheckStatus.ACK:
                self.send_mchs(True)
            case CheckStatus.NACK:
                self.send_mchs(False)
            case _:
                logging.warning("This condition must not be met")

        exectime = timeit.default_timer() - starttime
        logging.info("HealthControl was done in %.3f s", exectime)
        return
