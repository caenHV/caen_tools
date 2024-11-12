from abc import ABC, abstractmethod
from urllib.parse import urlparse

import logging

from caen_tools.connection.client import AsyncStreamClient
from .utils import InterlockResponse


class InterlockManagerBase(ABC):
    """Abstract interlock manager"""

    def __init__(self, interlock_db_uri: str):
        self._interlock_db_uri = interlock_db_uri

    @abstractmethod
    async def get_value(self) -> InterlockResponse:
        """Gets interlock value"""

    @abstractmethod
    async def set_value(self, value: bool | int) -> None:
        """Sets interlock value"""


class InterlockManagerSocket(InterlockManagerBase):
    """Manipulates socket vepp2kas to get interlock"""

    def __init__(self, interlock_db_uri: str):
        super().__init__(interlock_db_uri)
        self._cli = AsyncStreamClient(receive_time=5)
        self._parsed_uri = urlparse(interlock_db_uri)

    async def get_value(self) -> InterlockResponse | None:
        logging.debug("Use sockets to get interlock")

        message = bytes(f"n:{self._parsed_uri.path[1:]}|m:get\n", encoding="UTF-8")
        logging.debug("Pull interlock from socket (message: %s)", message)
        result = await self._cli.query(
            f"{self._parsed_uri.scheme}://{self._parsed_uri.netloc}", message
        )
        state = dict(
            map(lambda x: x.split(":"), result[1].decode("UTF-8").strip().split("|"))
        )
        logging.debug("Interlock data from socket: %s", state)
        return InterlockResponse(bool(int(state["val"])))

    async def set_value(self, value: bool | int) -> None:
        # TODO implement
        pass
