from urllib.parse import urlparse
import logging

import psycopg2

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import get_timestamp
from caen_tools.utils.receipt import Receipt
from caen_tools.SystemCheck.utils import send_udp_to_mchs_controller
from .metascript import Script
from .stuctures import InterlockState, InterlockParamsDict


class InterlockControl(Script):
    """Main class for the continious interlock control"""

    SENDER = "syscheck/ilockcontrol"
    DEVBACK = "devback"

    @staticmethod
    def rpt_usr_vlt() -> Receipt:
        return Receipt(
            sender=InterlockControl.SENDER,
            executor=InterlockControl.DEVBACK,
            title="last_user_voltage",
            params={},
        )

    @staticmethod
    def rpt_set_vlt(target_voltage: float) -> Receipt:
        return Receipt(
            sender=InterlockControl.SENDER,
            executor=InterlockControl.DEVBACK,
            title="set_voltage",
            params={"target_voltage": target_voltage},
        )

    @staticmethod
    def rpt_set_user_perm(enable_user_set: bool) -> Receipt:
        return Receipt(
            sender=InterlockControl.SENDER,
            executor=InterlockControl.DEVBACK,
            title="set_user_permission",
            params={"enable_user_set": enable_user_set},
        )

    def __init__(
        self,
        shared_parameters: InterlockParamsDict,
        devback_address: str,
        interlock_db_uri: str,
    ):
        logging.info("Init InterlockControl script")
        super().__init__(shared_parameters=shared_parameters, dependent_scripts=[])
        self.cli = AsyncClient({InterlockControl.DEVBACK: devback_address})
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
            logging.info(credentials)
            con = psycopg2.connect(**credentials)
        except psycopg2.OperationalError as e:
            logging.warning("Not connected to SND database: %s", e)
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
            logging.error(
                "Houston! We faced problems with getting interlock from the SND Database: %s",
                e,
            )

        return interlock_state

    async def on_start(self) -> None:
        await self.cli.query(InterlockControl.rpt_set_user_perm(False))

    async def on_stop(self) -> None:
        await self.cli.query(InterlockControl.rpt_set_user_perm(True))

    async def exec_function(self):
        """Main execution script for InterlockControl"""

        logging.info("Start interlock scipt")

        interlock = self.interlock

        if interlock == self.last_interlock:
            return

        new_ilock, old_iloc = interlock.current_state, self.last_interlock.current_state

        if new_ilock is True and old_iloc is False:
            trgresp = await self.cli.query(self.rpt_usr_vlt())
            user_voltage = trgresp.response.body["last_user_voltage"]
            voltage_mlt = self.shared_parameters.get("voltage_modifier")
            target_voltage = user_voltage * voltage_mlt
            logging.info("Interlock has been set. Set voltage %.3f", target_voltage)
            send_udp_to_mchs_controller(
                **self.shared_parameters["mchs"],
                ack=False,
            )
            await self.cli.query(self.rpt_set_vlt(target_voltage))

        elif new_ilock is False and old_iloc is True:
            trgresp = await self.cli.query(self.rpt_usr_vlt())
            target_voltage = trgresp.response.body["last_user_voltage"]
            logging.info(
                "Interlock has been turned off. Set voltage %.3f", target_voltage
            )
            send_udp_to_mchs_controller(
                **self.shared_parameters["mchs"],
                ack=True,
            )
            await self.cli.query(self.rpt_set_vlt(target_voltage))

        self.last_interlock = interlock
        self.shared_parameters["last_check"] = get_timestamp()
        logging.debug("Interlock check was completed")
        return

    def __del__(self):
        if self.conn is not None:
            self.conn.close()
        del self.cli
        return
