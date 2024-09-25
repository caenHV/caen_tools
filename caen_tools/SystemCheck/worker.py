"""Worker scenarios for system check"""

import asyncio
import logging

from caen_tools.SystemCheck.scripts import (
    HealthParameters,
    ManagerScript,
    InterlockControl,
    MChSWorker,
)


def run_worker(
    shared_parameters: dict,
    devback_address: str,
    mon_address: str,
    interlock_db_uri: str,
):
    """Worker running different scenarios for system control"""

    logging.info("Start worker %s, %s", devback_address, mon_address)

    mchs = MChSWorker(**shared_parameters["mchs"])
    interlock = InterlockControl(
        shared_parameters["interlock"], devback_address, interlock_db_uri
    )
    health = HealthParameters(
        shared_parameters["health"],
        devback_address,
        mon_address,
        mchs=mchs,
        stop_on_failure=[interlock],
    )
    manager = ManagerScript([interlock, health])

    # Start manager and included scenarios
    loop = manager.start()

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
