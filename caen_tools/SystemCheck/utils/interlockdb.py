import logging
from urllib.parse import urlparse
import psycopg2
from caen_tools.SystemCheck.scripts.structures import InterlockState


class InterlockManager:
    """Class for interaction with SND interlock database"""

    def __init__(self, interlock_db_uri: str):
        parsed_uri = urlparse(interlock_db_uri)
        self.__db_credentials = {
            "dbname": parsed_uri.path[1:],
            "user": parsed_uri.username,
            "password": parsed_uri.password,
            "host": parsed_uri.hostname,
            "port": parsed_uri.port,
        }
        self.__conn = self.__connect()

    def __connect(self):
        """Try to connect to database"""
        conn = None
        try:
            conn = psycopg2.connect(**self.__db_credentials)
        except psycopg2.OperationalError as e:
            logging.warning("Can't connect to SND database: %s", e)
        return conn

    @property
    def get_interlock(self) -> InterlockState:
        res = None
        if self.__conn is None:
            self.__conn = self.__connect()

        try:
            with self.__conn.cursor() as cursor:
                cursor.execute(
                    "SELECT value, time from values where property = 'KMD_Interlock';"
                )
                res = cursor.fetchone()
        except psycopg2.OperationalError as e:
            logging.warning("Not connected to SND database: %s", e)
            return InterlockState(current_state=True)
        except Exception as e:
            logging.warning(
                "Problems with getting interlock from the SND Database: %s.",
                e,
            )
            return InterlockState(current_state=True)

        if res is None or len(res) != 1:
            return InterlockState(current_state=True)

        return InterlockState(
            current_state=int(res[0]) > 0, timestamp=int(res[1].timestamp())
        )

    def __del__(self):
        if self.__conn is not None:
            self.__conn.close()
        return
