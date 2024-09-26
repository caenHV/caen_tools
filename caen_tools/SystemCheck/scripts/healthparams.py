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

    logger = logging.getLogger("HealthParameters")

    SENDER = "syscheck/health_params"

    def __init__(
        self,
        shared_parameters: HealthParametersDict,
        device_backend_address: str,
        monitor_address: str,
        mchs: MChSWorker,
        stop_on_failure: list[Script] | None = None,
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

    async def exec_function(self):
        logging.debug("Start HealthParameters script")
        starttime = timeit.default_timer()

        # Read current state of CAEN
        devpars = await self.cli.query(PreparedReceipts.get_params(self.SENDER))
        if isinstance(devpars.response, ReceiptResponseError):
            logging.error("No connection with DevBackend during HealthCheck")
            return

        self.logger.debug("Devpars %s", devpars)

        # Put these parameters into monitor
        moncheck = await self.cli.query(
            PreparedReceipts.put2mon(self.SENDER, devpars.response.body["params"])
        )
        if isinstance(moncheck.response, ReceiptResponseError):
            logging.error("No connection with Monitor during HealthCheck")
            return

        # Monitor provides status of uploaded data (ok or not ok)
        paramsok = moncheck.response.body["params_ok"]
        self.shared_parameters["last_check"] = get_timestamp()

        if not paramsok:
            self.logger.error("Bad deivce parameters. Emergency DownVoltage!")

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

        exectime = timeit.default_timer() - starttime
        self.logger.info("HealthParameters were done in %.3f s", exectime)
        return
