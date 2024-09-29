from abc import ABC, abstractmethod

import asyncio
import timeit
import logging

from .structures import MinimalScriptDict


class Script(ABC):

    def __init__(self, shared_parameters: MinimalScriptDict):
        self.task = None
        self.shared_parameters = shared_parameters

    @property
    def isrunning(self) -> bool:
        """Running script or not"""
        return self.task is not None

    def start_ifnot(self) -> None:
        """Starts a scenario loop if it not running yet"""

        self.shared_parameters["enable"] = True

        if self.isrunning:
            logging.warning("Scenario is already started")
            return

        asyncio.create_task(self.on_start())
        self.task = asyncio.create_task(self.loop())
        logging.info("Start scenario")
        return

    def stop(self) -> None:
        """Stops a scenario loop"""
        if not self.isrunning:
            logging.debug("Script is already stopped. No need stop")
            return

        self.shared_parameters["enable"] = False
        self.task = None
        asyncio.create_task(self.on_stop())
        logging.warning("Stop the script")
        return

    def trigger(self) -> None:
        """Asks script for turning on/off"""

        if self.shared_parameters["enable"] is True and self.task is None:
            self.start_ifnot()
        elif self.shared_parameters["enable"] is False and self.task is not None:
            self.stop()
        return

    def restart(self) -> None:
        """Restarts a loop"""
        self.stop()
        self.start_ifnot()
        return

    async def on_start(self) -> None:
        """Coroutine calling during start of the script"""
        return

    async def on_stop(self) -> None:
        """Coroutine calling on stop of the script"""
        return

    async def loop(self) -> bool:
        """Core coroutine that executes a function and sets a new task in time"""
        try:
            starttime = timeit.default_timer()
            await self.exec_function()
            exectime = timeit.default_timer() - starttime
            repeat_every = self.shared_parameters["repeat_every"]
            await asyncio.sleep(max(0, repeat_every - exectime))
            logging.debug("scenario exec function is completed")
        except asyncio.CancelledError:
            logging.info("Task was cancelled")
            return False
        except Exception as ex:
            logging.error("Task was failed", exc_info=True)
            self.task = None
            # self.shared_parameters["enable"] = False
            raise ex

        if self.shared_parameters["enable"] is True:
            self.task = asyncio.create_task(self.loop())
        else:
            self.task = None
        return True

    @abstractmethod
    async def exec_function(self):
        """A function to execute"""
