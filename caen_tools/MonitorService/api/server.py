from pathlib import Path
from typing import TypeAlias

import asyncio
import logging

from caen_tools.connection.server import RouterServer
from .monclass import Monitor
from .factory import APIFactory

Address: TypeAlias = str


class MessageProcessor:
    """Asynchronous request handler implementation"""

    def __init__(
        self,
        address: Address,
        dbpath: Path,
        param_file_path: Path,
        status_file_path: Path,
    ):
        self._dbs = RouterServer(address, "monitor")
        self._monclass = Monitor(dbpath, param_file_path, status_file_path)
        self._loop = asyncio.get_event_loop()
        self._semaphore = asyncio.Semaphore(5)

    async def execute_message(self) -> None:
        """Executes one receipt message"""

        client_address, receipt = await self._dbs.recv_receipt()
        logging.debug("Received %s from %s", receipt.title, receipt.sender)
        logging.debug("Full receipt %s", receipt)

        out_receipt = APIFactory.execute_receipt(receipt, self._monclass)
        await self._dbs.send_receipt(client_address, out_receipt)
        logging.debug("send response to client %s", client_address)
        return

    async def _process_messages(self):
        async with self._semaphore:
            asyncio.ensure_future(self._process_messages())
            await self.execute_message()
        return

    def listen(self):
        """Starts listening and request processing"""
        asyncio.ensure_future(self._process_messages())
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


def server(
    address: Address, dbpath: Path, param_file_path: Path, status_file_path: Path
):
    """Main function of monitor server"""

    logging.info("Start Monitor api server")
    processor = MessageProcessor(address, dbpath, param_file_path, status_file_path)

    try:
        processor.listen()
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Finish the program")
    finally:
        processor.close()

    return
