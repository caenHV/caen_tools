"""HealthControl: performs continious quality check 
of current parameters on CAEN device
"""

from typing import TypeAlias

import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError

from .metascript import Script
from .mchswork import MChSWorker
from .structures import HealthParametersDict, CheckResult, Codes
from .receipts import Services, PreparedReceipts

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
        self.__imon_key = "IMonH"
        self.__max_currents = max_currents

    async def on_stop(self):
        self.mchs.pop_keystate(self.MCHS_KEY)

    def form_answer(self, code: Codes) -> None:
        self.shared_parameters["last_check"] = CheckResult(code)
        return

    @staticmethod
    def __check_ch_status(pars: dict) -> bool:
        """Performs ChannelStatus check"""

        def good_status(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1][3:13]
            return int(st) == 0

        status = False
        try:
            ch_status_good = [good_status(val["ChStatus"]) for _, val in pars.items()]
            status = all(ch_status_good)
        except Exception as e:
            logging.warning("Can't check channels status. %s", e)
        logging.info("Channel statuses are %s", "good" if status else "bad")
        return status

    def __check_currents(self, pars: dict) -> bool:
        def max_current_key(ch_status: str) -> str:
            st = format(int(ch_status), "015b")[::-1][:13]
            key = "volt_change" if int(st[1]) == 1 or int(st[2]) == 1 else "steady"
            return key

        status = False
        try:
            currents_status = [
                val[self.__imon_key]
                < self.__max_currents[ch][max_current_key(val["ChStatus"])]
                for ch, val in pars.items()
            ]
            status = all(currents_status)
        except KeyError as e:
            logging.warning("Can't find channel max current in config: %s", e)
            status = False
        logging.info("Channel currents are %s", "good" if status else "bad")
        return status

    def perform_checks(self, params_dict: dict) -> bool:
        logging.debug("Perform parameters check: %s", params_dict)

        good_status = self.__check_ch_status(params_dict) and self.__check_currents(
            params_dict
        )
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
            PreparedReceipts.get_params(self.SENDER, [self.__imon_key, "ChStatus"])
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
