from time import time
from timeit import default_timer
import asyncio
import logging


class PeriodicalTask:
    """Class realizing self-reproduced periodical tasks"""

    def __init__(
        self,
        title: str,
        loop: asyncio.AbstractEventLoop,
        period: float,
        binding_coroutine,
    ):
        self._title = title
        self._period = period
        self._message = f"{title} initialized"
        self._timestamp = int(time())
        self._loop = loop
        self._task = None
        self._coroutine = binding_coroutine

    def _send_message(self, message: str) -> None:
        self._message = message
        self._timestamp = int(time())
        return

    def status(self) -> dict:
        """Returns main status of the task"""
        return dict(
            running=self._task is not None,
            title=self._title,
            period=self._period,
            message=self._message,
            binding_coroutine=self._coroutine,
            timestamp=self._timestamp,
        )

    def start(self, **kwargs) -> None:
        """Starts a task if possible"""

        if self._task is not None:
            self._send_message("Try to start already running")
        else:
            self._task = self._loop.create_task(self._coroutine_wrapper(**kwargs))
            self._send_message("Start periodical tasks")
            logging.info("Start periodical task %s", self._title)
        return

    def set_period(self, value: float) -> None:
        """Sets a period of the loop task"""
        self._period = value
        return

    async def stop(self) -> None:
        """Stops periodical task"""
        if self._task is not None:
            self._task.cancel()
            await asyncio.sleep(0.2)
            self._send_message("Shutdown task")
            logging.info("Shutdown %s", self._title)
        return

    async def _coroutine_wrapper(self, **kwargs):
        """executed coroutine wrapper"""

        try:
            start_time = default_timer()
            await self._coroutine(**kwargs)
            exec_time = default_timer() - start_time
            logging.info("Executed %s in %.3f", self._title, exec_time)
            await asyncio.sleep(self._period)
        except asyncio.CancelledError:
            logging.info("Cancelled %s", self._title)
            return
        except Exception:
            logging.warning("%s failed. Retry after period", self._title, exc_info=True)
            await asyncio.sleep(self._period)

        self._task = self._loop.create_task(self._coroutine_wrapper(**kwargs))
        return
