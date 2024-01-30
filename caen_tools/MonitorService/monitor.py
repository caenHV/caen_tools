"""MonitorService main file
"""

import argparse
import logging
import multiprocessing
from typing import Optional

from caen_tools.MonitorService.monclass import MonitorDB
from caen_tools.utils.utils import config_processor, get_default_logger
from caen_tools.MonitorService.ticketsender import ticket_sender
from caen_tools.connection.server import DeviceBackendServer
from caen_tools.MonitorService.query import QueryMaster


def monitor(
    dbpath: str,
    addr_front: str,
    addr_back: str,
    identity: str,
    device_identity: str,
    refreshtime: float,
    logger: Optional[logging.Logger] = None,
):
    if logger is None:
        logger = get_default_logger(logging.DEBUG)

    bkg_process = multiprocessing.Process(
        target=ticket_sender,
        args=(
            addr_front,
            refreshtime,
            identity,
            logger,
            device_identity,
            dbpath,
            10,
        ),
        daemon=True,
    )
    bkg_process.start()

    mondb = MonitorDB(dbpath, logger)
    serv = DeviceBackendServer(addr_back, identity)
    try:
        while True:
            from_addr, message = serv.recv()
            tkt = QueryMaster.deserialize(message)
            res_data_str = mondb.get_db_data(tkt)
            serv.send(res_data_str, from_addr)
            logger.debug("Return query data")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    finally:
        del serv
    return


def main():
    parser = argparse.ArgumentParser(description="Monitor microservice")
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        type=argparse.FileType("r"),
        help="Config file",
        nargs="?",
    )
    args = parser.parse_args()
    settings = config_processor(args.config)

    addr_front = settings.get("monitor", "proxy_frontend")
    addr_back = settings.get("monitor", "proxy_backend")
    dbpath = settings.get("monitor", "dbpath")
    identity = settings.get("monitor", "identity")
    device_identity = settings.get("monitor", "device_identity")
    refreshtime = settings.getfloat("monitor", "refreshtime")

    monitor(dbpath, addr_front, addr_back, identity, device_identity, refreshtime, None)


if __name__ == "__main__":
    main()
