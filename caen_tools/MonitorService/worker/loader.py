from asyncio import AbstractEventLoop
import asyncio
import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError
from .receipts import PreparedReceipts
from .utils import Address, Services, Codes


class LoaderControl:
    """Logic:
    1. asks devback for parameters (self._parameters)
    2. sends parameters to monitor service
    """

    SENDER = f"{Services.MONITOR}/loader"

    def __init__(self, device_backend: Address, monitor: Address, period: float = 1):
        self._cli = AsyncClient(
            {
                Services.DEVBACK: device_backend,
                Services.MONITOR: monitor,
            }
        )
        self._parameters = ["VMon", "IMonH", "IMonL", "ChStatus", "ImonRange"]
        self._repeat_every = period
        self._loop = None
        self._task = None

    def run(self) -> AbstractEventLoop:
        """Runs script loop"""

        logging.debug("Start loader loop")
        self._loop = asyncio.get_event_loop()
        self._task = self._loop.create_task(self._processor())
        return self._loop

    def close(self) -> None:
        """Shutdowns and cancels running tasks"""

        pending = asyncio.all_tasks(loop=self._loop)
        for task in pending:
            task.cancel()
            logging.debug("Close task %s", task)
        logging.info("Final program close")
        return

    async def _processor(self) -> None:
        """Core coroutine that executes a function and sets a new task in time"""
        try:
            starttime = timeit.default_timer()
            await self._exec_function()
            exectime = timeit.default_timer() - starttime
            logging.info("LoaderControl was done in %.3f s", exectime)

            await asyncio.sleep(max(0, self._repeat_every - exectime))
            logging.debug("scenario exec function is completed")
        except asyncio.CancelledError:
            logging.info("Task was cancelled")
            return False
        except Exception as ex:
            logging.error("Task was failed", exc_info=True)
            self._task = None
            raise ex

        self._task = self._loop.create_task(self._processor())
        return

    def _form_answer(self, code: Codes):
        logging.debug("Loader last status is %s", code)
        return

    async def _exec_function(self):

        # 1. Get parameters from DEVBACK
        devpars = await self._cli.query(
            PreparedReceipts.get_params(self.SENDER, self._parameters)
        )
        if isinstance(devpars.response, ReceiptResponseError):
            logging.error("No connection with DevBackend during LoaderControl")
            self._form_answer(Codes.DEVBACK_ERROR)
            return

        # 2. Put parameters into MON
        moncheck = await self._cli.query(
            PreparedReceipts.put2mon(self.SENDER, devpars.response.body["params"])
        )
        if isinstance(moncheck.response, ReceiptResponseError):
            logging.error("No connection with Monitor during LoaderControl")
            self._form_answer(Codes.MONITOR_ERROR)
            return

        # 3. Finish
        self._form_answer(Codes.OK)
        return
