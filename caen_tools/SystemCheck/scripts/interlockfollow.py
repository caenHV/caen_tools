import logging

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import get_timestamp
from .metascript import Script
from .stuctures import InterlockState, InterlockParamsDict
from .receipts import PreparedReceipts, Services
from .interlock_manager import InterlockManager


class InterlockControl(Script):
    """Main class for the continious interlock control"""

    logger = logging.getLogger("InterlockControl class")

    SENDER = "syscheck/ilockcontrol"

    def __init__(
        self,
        shared_parameters: InterlockParamsDict,
        devback_address: str,
        interlock_db_uri: str,
    ):
        self.logger.info("Init InterlockControl script")
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient({Services.DEVBACK: devback_address})
        self.__intrlck_manager = InterlockManager(interlock_db_uri)
        self.last_interlock = InterlockState()

    @property
    def interlock(self) -> InterlockState:
        """Returns last value of interlock state"""
        interlock_state = self.__intrlck_manager.get_interlock
        return interlock_state

    async def on_start(self) -> None:
        self.logger.info("Start interlock control. Disable user to set voltage")
        await self.cli.query(PreparedReceipts.set_user_permission(self.SENDER, False))

    async def on_stop(self) -> None:
        self.logger.info("Stop interlock control. Enable user to set voltage")
        await self.cli.query(PreparedReceipts.set_user_permission(self.SENDER, True))

    async def exec_function(self):
        """Main execution script for InterlockControl"""

        self.logger.info("Start interlock scipt")
        interlock = self.interlock
        if interlock == self.last_interlock:
            logging.debug("No change in interlock")
            return

        new_ilock, old_iloc = interlock.current_state, self.last_interlock.current_state

        if new_ilock is True and old_iloc is False:
            trgresp = await self.cli.query(
                PreparedReceipts.last_user_voltage(self.SENDER)
            )
            user_voltage = trgresp.response.body["last_user_voltage"]
            voltage_mlt = self.shared_parameters.get("voltage_modifier")
            target_voltage = user_voltage * voltage_mlt
            self.logger.info("Interlock has been set. Set voltage %.3f", target_voltage)

            await self.cli.query(
                PreparedReceipts.set_voltage(self.SENDER, target_voltage)
            )

        elif new_ilock is False and old_iloc is True:
            trgresp = await self.cli.query(
                PreparedReceipts.last_user_voltage(self.SENDER)
            )
            target_voltage = trgresp.response.body["last_user_voltage"]
            self.logger.info(
                "Interlock has been turned off. Set voltage %.3f", target_voltage
            )

            await self.cli.query(
                PreparedReceipts.set_voltage(self.SENDER, target_voltage)
            )

        self.last_interlock = interlock
        self.shared_parameters["last_check"] = get_timestamp()
        self.logger.debug("Interlock check was completed")
        return

    def __del__(self):
        del self.cli
        return
