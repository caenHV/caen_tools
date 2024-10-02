"""HealthControl: performs continuous quality check 
of current parameters on CAEN device
"""

import time
from typing import TypeAlias

import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError

from .metascript import Script
from .mchswork import MChSWorker
from .structures import HealthParametersDict, CheckResult, Codes
from .receipts import Services, PreparedReceipts
from ..utils import RampDownInfo

Address: TypeAlias = str


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

    @staticmethod
    def __check_ch_status(pars: dict) -> tuple[bool, bool]:
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

        def good_status(ch_status: str) -> tuple[bool, bool]:
            st = format(int(ch_status), "015b")[::-1][3:13]
            is_good = int(st) == 0
            is_only_overvoltage = st[1] == "1" and st[0] == "0" and int(st[2:]) == 0
            return is_good, is_only_overvoltage

        status = False
        bad_channels = []
        only_overvolt_channels = []
        try:
            ch_status_good = {
                ch: good_status(val["ChStatus"]) for ch, val in pars.items()
            }
            bad_channels = [ch for ch, stat in ch_status_good.items() if not stat[0]]
            only_overvolt_channels = [
                ch for ch, stat in ch_status_good.items() if stat[1]
            ]
            status = len(bad_channels) == 0
            is_only_overvoltage = (
                len(bad_channels) != 0 and only_overvolt_channels == bad_channels
            )
            logging.debug("Channel statuses: %s", ch_status_good)
        except Exception as e:
            logging.warning("Can't check channels status. %s", e)

        if not status:
            logging.warning(
                f"Channels {bad_channels} statuses are bad. Channels {only_overvolt_channels} are in over voltage."
            )
        return status, is_only_overvoltage

    def __trip_time_check(self, pars: dict) -> bool:
        """Returns true if trip time is not exceeded."""

        def check_status(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1][2]
            return st == "1"

        status = False
        ch_trip_status: dict = {}

        def check_time(info: RampDownInfo) -> bool:
            """If is_rdown time exceeds trip_time returns False, otherwise returns True."""
            if info.timestamp is None:
                return True
            return time.time() - info.timestamp < info.trip_time

        try:
            for ch, val in pars.items():
                new_status = check_status(val["ChStatus"])
                prev_status = self.__rdown_info[ch].is_rdown
                ch_status = True

                if new_status and not prev_status:
                    self.__rdown_info[ch].is_rdown = True
                    self.__rdown_info[ch].timestamp = time.time()

                if not new_status and prev_status:
                    self.__rdown_info[ch].is_rdown = False
                    self.__rdown_info[ch].timestamp = None

                if self.__rdown_info[ch].is_rdown:
                    ch_status = check_time(self.__rdown_info[ch])
                ch_trip_status[ch] = ch_status

            status = all(ch_trip_status.values())
            if not status:
                logging.warning(
                    f"Channels {[ch for ch, stat in ch_trip_status.items() if not stat]} exceeded trip time."
                )
        except Exception as e:
            logging.debug("Can't check ramp_down bit in channels status. %s", e)

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

    def perform_checks(self, params_dict: dict) -> bool:
        """All checks of the recieved parameters are here"""

        logging.debug("Perform parameters check: %s", params_dict)

        is_trip_time_ok = self.__trip_time_check(params_dict)
        is_status_ok, is_only_overvoltage = self.__check_ch_status(params_dict)
        is_current_ok = self.__check_currents(params_dict)
        if is_only_overvoltage and is_trip_time_ok:
            is_status_ok = True
        good_status = is_status_ok and is_current_ok

        if not good_status:
            logging.warning("Bad parameters found: %s", params_dict)
        return good_status

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
                self.SENDER, ["IMonH", "IMonL", "ImonRange", "ChStatus"]
            )
        )
        if isinstance(devback_params.response, ReceiptResponseError):
            logging.warning("Error from DeviceBackend %s", devback_params.response)
            self.form_answer(Codes.DEVBACK_ERROR)
            return

        params_dict = devback_params.response.body["params"]
        params_ok: bool = self.perform_checks(params_dict)

        if not params_ok:
            await self.failure_actions()
            return

        self.send_mchs(True)

        exectime = timeit.default_timer() - starttime
        logging.info("HealthControl was done in %.3f s", exectime)
        return
