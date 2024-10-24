from urllib.parse import urlparse

import logging

import psycopg
from caen_tools.connection.client import AsyncStreamClient
from caen_tools.SystemCheck.scripts.structures import InterlockState


class InterlockManager:
    """Class for interaction with SND interlock database"""

    def __init__(self, interlock_db_uri: str):
        """For reading fake interlock value from user defined file

        Parameters
        ----------
        interlock_db_uri: str 
            connect addres to interlock location
            reading can be from
            - SND postgres database: postgresql://login:pass@address/table
            - VEPP2k socket: tcp://address/key
            - text file: fake://./interlock.txt
        """

        self._cli = AsyncStreamClient(receive_time=5)

        self._fakepath = None
        if interlock_db_uri.startswith("fake://"):
            self._fakepath = interlock_db_uri.split("://")[-1]
            return

        parsed_uri = urlparse(interlock_db_uri)
        self._db_credentials = {
            "dbname": parsed_uri.path[1:],
            "user": parsed_uri.username,
            "password": parsed_uri.password,
            "host": parsed_uri.hostname,
            "port": parsed_uri.port,
        }
        self._parsed_uri = parsed_uri

    async def _postgres_pulling(self) -> InterlockState:
        """Pulls interlock state from postgres database"""

        try:
            async with await psycopg.AsyncConnection.connect(
                **self._db_credentials
            ) as aconn:
                async with aconn.cursor() as acur:
                    await acur.execute(
                        "SELECT value, time from values where property = 'KMD_Interlock';"
                    )
                    res = await acur.fetchone()
                    return InterlockState(
                        current_state=int(res[0]) > 0, timestamp=int(res[1].timestamp())
                    )
        except Exception:
            logging.warning("Interlock reading problem (from SND db)", exc_info=True)

        return InterlockState(True)

    async def _socket_pulling(self) -> InterlockState:
        """Pulls interlock state from socket"""

        message = bytes(
            rf"n:{self._db_credentials['dbname']}|m:get\n", encoding="UTF-8"
        )
        logging.debug("Pull interlock from socket (message: %s)", message)
        result = await self._cli.query(
            f"{self._parsed_uri.scheme}://{self._parsed_uri.netloc}", message
        )

        if result is None:
            return InterlockState(True)

        state = dict(
            map(lambda x: x.split(":"), result[1].decode("UTF-8").strip().split("|"))
        )
        logging.debug("Interlock data from socket: %s", state)
        return InterlockState(bool(int(state["val"])))

    async def get_interlock(self) -> InterlockState:
        """Returns current interlock state"""

        if self._fakepath:
            with open(self._fakepath, "r", encoding="utf-8") as f:
                interlock = int(f.read())
            logging.debug("Fake interlock value is %s", interlock)
            return InterlockState(interlock)

        interlock = InterlockState(True)

        match self._parsed_uri.scheme:
            case "postgresql":
                logging.debug("Use postgres to get interlock")
                interlock = await self._postgres_pulling()
            case "tcp":
                logging.debug("Use sockets to get interlock")
                interlock = await self._socket_pulling()
            case _:
                logging.warning("Wrong protocol %s", self._parsed_uri.scheme)

        return interlock
