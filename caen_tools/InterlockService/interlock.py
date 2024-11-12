import logging
import zmq

from caen_tools.connection.serverprocessor import ServerManager
from caen_tools.connection.looptask import PeriodicalTask
from caen_tools.utils.receipt import Receipt, ReceiptResponse
from caen_tools.utils.resperrs import RResponseErrors
from caen_tools.utils.statuscodes import StatusCode
from .utils import Address, InterlockResponse, Mode
from .ilockusage import InterlockManagerSocket
from .database import IlkDBMangager


class InterlockProcessor(ServerManager):
    """Defines requests to outer interlock"""

    IDENTITY = "interlock"
    NUM_ASYNC_TASKS = 5
    PERIOD_CLEANER = 3600 * 24

    def __init__(self, bind_address: Address, connect_address: Address, db_path: str):
        super().__init__(bind_address, self.IDENTITY, self.NUM_ASYNC_TASKS)
        self._database = IlkDBMangager(
            db_path,
            dict(
                bind_address=bind_address,
                socket=connect_address,
            ),
        )
        logging.debug("Start: %s", self._database.settings)
        self._manager = InterlockManagerSocket(connect_address)
        self._cleaner = PeriodicalTask(
            "cleaner", self._loop, self.PERIOD_CLEANER, self._task_cleandb
        )

    async def _task_cleandb(self) -> None:
        """Removes old rows from the database"""
        self._database.remove_before(self.PERIOD_CLEANER)

    async def start_task_cleaner(self) -> None:
        """Starts running cleaner"""
        self._cleaner.start()

    async def api_get_value(self) -> ReceiptResponse:
        """get_value endpoint"""
        match self._database.mode:
            case Mode.SOCKET:
                response: InterlockResponse = await self._manager.get_value()
                self._database.interlock = response.value
            case Mode.MANUAL:
                response = InterlockResponse(value=self._database.interlock)

        return self.__response(response)

    async def api_report(self) -> ReceiptResponse:
        """report: Sends service status report"""
        return self.__response({})

    async def api_set_mode(self, mode: Mode) -> ReceiptResponse:
        """set_mode endpoint: Sets interlock mode (manual or socket)"""
        self._database.mode = mode
        response = await self.api_status()
        return response

    async def api_set_value(self, value: bool) -> ReceiptResponse:
        """set_value endpoint: Sets interlock value (manual mode only)"""
        if self._database.settings["mode"] != Mode.MANUAL:
            return RResponseErrors.NotImplemented("Set available in manual mode only")

        self._database.interlock = value
        return self.__response({})

    async def api_status(self) -> ReceiptResponse:
        """Returns status of the microservice"""
        return self.__response(self._database.settings)

    def __response(
        self, body: dict, statuscode: StatusCode = StatusCode.SUCCESS
    ) -> ReceiptResponse:
        return ReceiptResponse(statuscode=statuscode, body=body)

    async def handle_receipt(self, receipt: Receipt) -> Receipt:
        """Processes input receipt and returns answer"""

        try:
            receipt = await super().handle_receipt(receipt)
        except TypeError:
            logging.warning("API request with wrong parameters", exc_info=True)
            receipt.response = RResponseErrors.ForbiddenMethod("Wrong arguments passed")
        except zmq.error.Again:
            logging.warning("No connection", exc_info=True)
            receipt.response = RResponseErrors.GatewayTimeout(
                "Broken pipe to outer source"
            )

        return receipt

    def close(self):
        super().close()
        self._database.close()
