import asyncio
import logging

from caen_tools.SystemCheck.scripts.metascript import Script


class ManagerScript(Script):
    """Main script to manage (turn on / off) all other scripts every `repeat_every` seconds"""

    def __init__(self, manage_scripts: list[Script], repeat_every: int = 1):
        super().__init__(
            {"enable": True, "repeat_every": repeat_every},
            dependent_scripts=manage_scripts,
        )
        logging.info("ManagerScript script was init")

    def start(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.loop())
        return loop

    async def exec_function(self):
        """Polls all manage_scripts and for updating their status"""

        for script in self.dependent_scripts:
            script.trigger()

        return
