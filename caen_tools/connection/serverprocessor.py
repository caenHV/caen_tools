from abc import ABC, abstractmethod
from timeit import default_timer
import asyncio
import logging

from caen_tools.connection.server import RouterServer
from caen_tools.utils.receipt import Receipt, ReceiptResponse
from caen_tools.utils.resperrs import RResponseErrors


class ServerManager(ABC):
    """Base class server manager
    All API endpoints must be named like `api_...`
    """

    def __init__(self, bind_address: str, identity: str, num_async_tasks: int):
        self._server = RouterServer(bind_address, identity)
        self._sem = asyncio.Semaphore(num_async_tasks)
        self._loop = asyncio.get_event_loop()

    async def wrongroute(self) -> ReceiptResponse:
        """Wrong route endpoint"""
        return RResponseErrors.NotFound("Route not found")

    @abstractmethod
    async def handle_receipt(self, receipt: Receipt) -> Receipt:
        """Processes input receipt and returns answer"""

        start_time = default_timer()
        api_endpoint = f"api_{receipt.title}"
        logging.debug("Call for api %s", api_endpoint)
        if hasattr(self, api_endpoint) and callable(
            api_route := getattr(self, api_endpoint)
        ):
            receipt.response = await api_route(**receipt.params)
        else:
            receipt.response = await self.wrongroute()
        exec_time = default_timer() - start_time

        logging.info(
            "Receipt %s from %s: executed in %.4fs",
            receipt.title,
            receipt.sender,
            exec_time,
        )

        return receipt

    async def _process_messages(self) -> None:
        """Waits a message, processes it and sends back a response"""

        async with self._sem:
            asyncio.ensure_future(self._process_messages())

            client_address, receipt = await self._server.recv_receipt()
            logging.debug("Received %s", receipt)

            response = await self.handle_receipt(receipt)
            logging.debug(response)
            await self._server.send_receipt(client_address, response)
            logging.debug("send response to client %s", client_address)

        return

    def listen(self, on_start_coros: list | None = None):
        """Starts listening and request processing"""
        asyncio.ensure_future(self._process_messages())
        if on_start_coros is not None:
            for coro in on_start_coros:
                asyncio.ensure_future(coro, loop=self._loop)
        self._loop.run_forever()
        return

    def close(self):
        """Closes tasks"""
        pending = asyncio.all_tasks(loop=self._loop)
        for task in pending:
            task.cancel()
            logging.debug("Close task %s", task)
        logging.info("Final program close")
        return
