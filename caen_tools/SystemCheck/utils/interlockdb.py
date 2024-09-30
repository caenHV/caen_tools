from urllib.parse import urlparse

import logging

import psycopg
from caen_tools.SystemCheck.scripts.structures import InterlockState


class InterlockManager:
    """Class for interaction with SND interlock database"""

    def __init__(self, interlock_db_uri: str):
        """For reading fake interlock value from user defined file
        use interlock_db_uri in format like: fake://./interlock.txt
        """

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

    async def get_interlock(self) -> InterlockState:
        """Returns current interlock state"""

        if self._fakepath:
            with open(self._fakepath, "r", encoding="utf-8") as f:
                interlock = int(f.read())
            logging.debug("Fake interlock value is %s", interlock)
            return InterlockState(interlock)

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
