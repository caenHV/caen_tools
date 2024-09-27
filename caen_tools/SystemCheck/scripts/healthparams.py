import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import get_timestamp
from caen_tools.utils.receipt import ReceiptResponseError

from .metascript import Script
from .structures import HealthParametersDict
from .receipts import PreparedReceipts, Services
from .mchswork import MChSWorker


class HealthParameters(Script):
    """The script performs checks of last parameters from the caen device"""

    SENDER = "syscheck/health_params"

    def __init__(
        self,
        shared_parameters: HealthParametersDict,
        device_backend_address: str,
        monitor_address: str,
        mchs: MChSWorker,
        stop_on_failure: list[Script] | None = None,
        imon_key: str = "IMonH",
        max_currents: dict[str, dict[str, float]] = dict(),
    ):
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient(
            {
                Services.MONITOR: monitor_address,
                Services.DEVBACK: device_backend_address,
            }
        )
        self.dependent_scripts = stop_on_failure if stop_on_failure is not None else []
        self.mchs = mchs
        self.__imon_key = imon_key
        self.__max_currents = max_currents

    @staticmethod
    def __check_ch_status(pars: dict) -> bool:
        status = False
        try:
            ch_status_list = [
                int(bin(int(val["ChStatus"]))[2:]) > 111 for _, val in pars.items()
            ]
            status = not any(ch_status_list)
        except Exception as e:
            logging.warning("Can't check channels status. %s", e)
        logging.info("Channels status is %s", "good" if status else "bad")
        return status

    def __check_currents(self, pars: dict) -> bool:
        status = False

        def max_cur_key(ch_status: str) -> str:
            st = format(int(ch_status), "015b")[::-1]
            key = "volt_change" if int(st[1]) == 1 or int(st[2]) == 1 else "steady"
            return key

        try:
            currents_status = [
                val[self.__imon_key]
                < self.__max_currents[ch][max_cur_key(val["ChStatus"])]
                for ch, val in pars.items()
            ]
            status = all(currents_status)
        except KeyError as e:
            logging.warning("Can't find channel max current in config: %s", e)
            status = False
        logging.info("Channels currents are %s", "good" if status else "bad")
        return status

    def are_parameters_ok(self, pars: dict) -> bool:
        params_ok = self.__check_ch_status(pars) and self.__check_currents(pars)
        return params_ok

    async def exec_function(self):
        logging.debug("Start HealthParameters script")
        starttime = timeit.default_timer()

        # Read current state of CAEN
        devpars = await self.cli.query(PreparedReceipts.get_params(self.SENDER))
        if isinstance(devpars.response, ReceiptResponseError):
            logging.error("No connection with DevBackend during HealthCheck")
            return

        logging.debug("Devpars %s", devpars)

        paramsok = self.are_parameters_ok(devpars.response.body["params"])
        self.shared_parameters["last_check"] = get_timestamp()

        if not paramsok:
            logging.error("Bad deivce parameters. Emergency DownVoltage!")

            # Stop all dependent scripts
            for script in self.dependent_scripts:
                script.stop()

            # Send bad news on mchs
            self.mchs.set_state(health_params=False)
            self.mchs.send_state()

            await self.cli.query(PreparedReceipts.down(self.SENDER))
            return

        # Send good news on mchs
        self.mchs.set_state(health_params=True)
        self.mchs.send_state()

        # Put parameters into monitor
        moncheck = await self.cli.query(
            PreparedReceipts.put2mon(self.SENDER, devpars.response.body["params"])
        )
        if isinstance(moncheck.response, ReceiptResponseError):
            logging.error("No connection with Monitor during HealthCheck")
            return

        exectime = timeit.default_timer() - starttime
        logging.info("HealthParameters were done in %.3f s", exectime)
        return
