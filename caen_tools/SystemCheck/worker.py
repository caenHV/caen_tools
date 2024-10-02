"""Worker scenarios for system check"""

import asyncio
import logging

from caen_tools.SystemCheck.scripts import (
    ManagerScript,
    MChSWorker,
    LoaderControl,
    InterlockControl,
    HealthControl,
    RelaxControl,
    ReducerControl,
)
from .utils import InterlockManager


def run_worker(
    shared_parameters: dict,
    devback_address: str,
    mon_address: str,
    interlock_db_uri: str,
    max_currents: dict,
    ramp_down_trip_time: dict,
):
    """Worker running different scenarios for system control"""

    logging.info("Start worker %s, %s", devback_address, mon_address)

    # Specific utility classes
    mchs = MChSWorker(**shared_parameters["mchs"])
    interlockdb = InterlockManager(interlock_db_uri)

    # A number of running scripts
    loader = LoaderControl(shared_parameters["loader"], devback_address, mon_address)
    interlock = InterlockControl(shared_parameters["interlock"], interlockdb, mchs)
    relax = RelaxControl(shared_parameters["relax"], devback_address, interlockdb)
    reducer = ReducerControl(
        shared_parameters["reducer"], devback_address, interlockdb, mchs, relax
    )
    health = HealthControl(
        shared_parameters["health"],
        devback_address,
        mon_address,
        mchs,
        max_currents,
        ramp_down_trip_time,
        [relax, reducer],
    )

    manager = ManagerScript([loader, interlock, relax, reducer, health])

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
