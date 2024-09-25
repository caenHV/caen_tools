from urllib.parse import urlparse
import logging

import psycopg2

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import get_timestamp
from .metascript import Script
from .stuctures import InterlockState, InterlockParamsDict
from .receipts import PreparedReceipts, Services


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
        self.__interlock_db_uri = interlock_db_uri
        self.conn = self.__connect_database()
        self.last_interlock = InterlockState()

    def __connect_database(self):
        parsed_uri = urlparse(self.__interlock_db_uri)
        credentials = {
            "dbname": parsed_uri.path[1:],
            "user": parsed_uri.username,
            "password": parsed_uri.password,
            "host": parsed_uri.hostname,
            "port": parsed_uri.port,
        }
        try:
            self.logger.info(credentials)
            con = psycopg2.connect(**credentials)
        except psycopg2.OperationalError as e:
            self.logger.warning("Not connected to SND database: %s", e)
            con = None

        return con

    @property
    def interlock(self) -> InterlockState:
        """Returns last value of interlock state"""

        interlock_state = self.last_interlock

        if self.conn is None:
            self.conn = self.__connect_database()

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT value, time from values where property = 'KMD_Interlock';"
                )
                res = cursor.fetchone()
                interlock_state = InterlockState(bool(res[0]))
        except Exception as e:
            self.logger.error(
                "Houston! We faced problems with getting interlock from the SND Database: %s",
                e,
            )

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
        if self.conn is not None:
            self.conn.close()
        del self.cli
        return
