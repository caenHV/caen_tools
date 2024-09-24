import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.SystemCheck.scripts.metascript import Script
from caen_tools.utils.utils import get_timestamp
from caen_tools.utils.receipt import Receipt
from caen_tools.SystemCheck.utils import send_udp_to_mchs_controller
from .stuctures import HealthParametersDict


class HealthParameters(Script):
    """The script performs checks of last parameters from the caen device"""

    SENDER = "syscheck/health_params"
    MONITOR = "monitor"
    DEVBACK = "device_backend"

    @staticmethod
    def rpt_get_params() -> Receipt:
        return Receipt(
            sender=HealthParameters.SENDER,
            executor=HealthParameters.DEVBACK,
            title="params",
            params={},
        )

    @staticmethod
    def rpt_down() -> Receipt:
        return Receipt(
            sender=HealthParameters.SENDER,
            executor=HealthParameters.DEVBACK,
            title="down",
            params={},
        )

    @staticmethod
    def rpt_put2mon(params) -> Receipt:
        return Receipt(
            sender=HealthParameters.SENDER,
            executor=HealthParameters.MONITOR,
            title="send_params",
            params={"params": params},
        )

    @staticmethod
    def rpt_setvoltage(target_voltage: float) -> Receipt:
        return Receipt(
            sender=HealthParameters.SENDER,
            executor=HealthParameters.DEVBACK,
            title="set_voltage",
            params={"target_voltage": target_voltage},
        )

    @staticmethod
    def rpt_getvoltage() -> Receipt:
        return Receipt(
            sender=HealthParameters.SENDER,
            executor=HealthParameters.DEVBACK,
            title="last_user_voltage",
            params={},
        )

    def __init__(
        self,
        shared_parameters: HealthParametersDict,
        device_backend_address: str,
        monitor_address: str,
        dependent_scripts: list[Script] | None = None,
    ):
        super().__init__(
            shared_parameters=shared_parameters,
            dependent_scripts=dependent_scripts,
        )
        self.cli = AsyncClient(
            {
                HealthParameters.MONITOR: monitor_address,
                HealthParameters.DEVBACK: device_backend_address,
            }
        )

    async def exec_function(self):
        starttime = timeit.default_timer()

        # Read current state of CAEN
        devpars = await self.cli.query(HealthParameters.rpt_get_params())
        logging.debug("Devpars %s", devpars)

        # Put these parameters into monitor
        moncheck = await self.cli.query(
            HealthParameters.rpt_put2mon(devpars.response.body["params"])
        )

        # Monitor provides status of uploaded data (ok or not ok)
        paramsok = moncheck.response.body["params_ok"]
        self.shared_parameters["last_check"] = get_timestamp()

        if not paramsok:
            logging.error("Bad deivce parameters. Emergency DownVoltage!")

            # Stop all dependent scripts
            self.stop_deps()

            send_udp_to_mchs_controller(
                **self.shared_parameters["mchs"],
                ack=False,
            )
            await self.cli.query(HealthParameters.rpt_down())

            # NOT Stop itself
            return

        send_udp_to_mchs_controller(
            **self.shared_parameters["mchs"],
            ack=True,
        )
        exectime = timeit.default_timer() - starttime
        logging.info("HealthParameters was done in %.3f s", exectime)
        return
