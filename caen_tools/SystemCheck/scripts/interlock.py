"""InterlockControl: polls SND database about interlock 
and sends to MChS current status"""

import timeit
import logging

from caen_tools.SystemCheck.utils.interlockdb import InterlockManager
from .metascript import Script
from .structures import InterlockParametersDict
from .mchswork import MChSWorker


class InterlockControl(Script):
    """Logic:
    1. Get interlock from SND database
    2. Send current status to MChS
    """

    def __init__(
        self,
        shared_parameters: InterlockParametersDict,
        interlockdb: InterlockManager,
        mchs: MChSWorker,
    ):
        super().__init__(shared_parameters=shared_parameters)
        self.mchs = mchs
        self.db = interlockdb

    async def exec_function(self):
        logging.debug("Start HealthControl script")
        starttime = timeit.default_timer()

        # 1. Get state
        interlock = await self.db.get_interlock()

        # 2. Send state
        self.mchs.set_state(nointerlock=not interlock.current_state)
        self.mchs.send_state()

        exectime = timeit.default_timer() - starttime
        logging.info("InterlockControl was done in %.3f s", exectime)
        return

    async def on_stop(self):
        self.mchs.pop_keystate("nointerlock")
