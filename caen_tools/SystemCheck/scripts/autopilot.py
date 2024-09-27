import logging

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import get_timestamp
from caen_tools.SystemCheck.utils import InterlockManager

from .metascript import Script
from .structures import InterlockState, AutopilotParamsDict
from .receipts import PreparedReceipts, Services


class AutopilotControl(Script):
    """Main class for the continious interlock control"""

    SENDER = "syscheck/ilockcontrol"

    def __init__(
        self,
        shared_parameters: AutopilotParamsDict,
        devback_address: str,
        interlock_db_uri: str,
    ):
        logging.info("Init AutopilotControl script")
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient({Services.DEVBACK: devback_address})
        self.__intrlck_manager = InterlockManager(interlock_db_uri)
        self.last_interlock = InterlockState()
        self.__is_locked = False
        self.__target_voltage = self.shared_parameters.get("target_voltage", 0)

    @property
    def interlock(self) -> InterlockState:
        """Returns last value of interlock state"""
        interlock_state = self.__intrlck_manager.get_interlock
        return interlock_state

    async def on_start(self) -> None:
        logging.info("Start interlock control. Disable user to set voltage")
        await self.cli.query(PreparedReceipts.set_user_permission(self.SENDER, False))

    async def on_stop(self) -> None:
        logging.info("Stop interlock control. Enable user to set voltage")
        await self.cli.query(PreparedReceipts.set_user_permission(self.SENDER, True))

    async def exec_function(self):
        """Main execution script for AutopilotControl"""

        logging.info("Start interlock scipt")
        interlock = self.interlock
        if interlock == self.last_interlock:
            logging.debug("No change in interlock")
            return

        new_ilock = interlock.current_state

        if new_ilock is True and self.__is_locked is False:
            target_voltage = self.__target_voltage
            voltage_mlt: float = self.shared_parameters.get("voltage_modifier", 0)
            ilock_target_voltage = target_voltage * voltage_mlt
            logging.info(
                "Interlock has been set. Set voltage %.3f", ilock_target_voltage
            )
            self.__is_locked = True
            await self.cli.query(
                PreparedReceipts.set_voltage(self.SENDER, ilock_target_voltage)
            )

        elif new_ilock is False and self.__is_locked is True:
            target_voltage = self.__target_voltage
            logging.info(
                "Interlock has been turned off. Set voltage %.3f", target_voltage
            )
            self.__is_locked = False
            await self.cli.query(
                PreparedReceipts.set_voltage(self.SENDER, target_voltage)
            )

        self.last_interlock = interlock
        self.shared_parameters["last_check"] = get_timestamp()
        logging.debug("Interlock check was completed")
        return

    def __del__(self):
        del self.cli
        return
