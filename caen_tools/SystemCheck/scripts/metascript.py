from abc import ABC, abstractmethod
from typing import TypedDict

import asyncio
import timeit
import logging


class SharedParamsDict(TypedDict):
    """Defines a structure of shared parameters dictionary"""

    enable: bool
    repeat_every: int


class Script(ABC):

    def __init__(
        self,
        shared_parameters: SharedParamsDict,
        dependent_scripts: list["Script"] | None = None,
    ):
        self.task = None
        self.shared_parameters = shared_parameters
        self.dependent_scripts = (
            dependent_scripts if dependent_scripts is not None else []
        )

    def start_ifnot(self) -> None:
        """Starts a scenario loop if it not running yet"""

        self.shared_parameters["enable"] = True

        if self.task is not None:
            logging.warning("Scenario is already started")
            return

        asyncio.create_task(self.on_start())
        self.task = asyncio.create_task(self.loop())
        logging.info("Start scenario")
        return

    def stop(self) -> None:
        """Stops a scenario loop"""
        self.shared_parameters["enable"] = False
        self.task = None
        asyncio.create_task(self.on_stop())
        logging.info("Stop scenario")
        return

    def stop_deps(self) -> None:
        """Stops all dependent scripts"""

        logging.warning("Call stop all dependents for the script")
        for dep_script in self.dependent_scripts:
            dep_script.stop_all()
            dep_script.stop()

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

        if self.shared_parameters["enable"] is True:
            self.task = asyncio.create_task(self.loop())
        else:
            self.task = None
        return True

    @abstractmethod
    async def exec_function(self):
        """A function to execute"""
