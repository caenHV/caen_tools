"""Worker scenarios for system check"""

import asyncio
import logging

from caen_tools.connection.client import AsyncClient
from caen_tools.SystemCheck.scenarios import base_scenario


def run_worker(shared_parameters: dict, devback_address: str, mon_address: str):
    """Worker running different scenarios for system control"""

    logging.info("Start worker %s, %s", devback_address, mon_address)

    cli = AsyncClient({"devback": devback_address, "monitor": mon_address}, 10)

    loop = asyncio.get_event_loop()

    # Add all using scenarios in the loop
    loop.create_task(base_scenario(cli, shared_parameters))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt. Finish syscheck loop")
    finally:
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
            logging.debug("Close task %s", task)
        logging.info("Final close")
    return
