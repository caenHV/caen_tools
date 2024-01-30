import logging
import time
from typing import Optional

import zmq

from caen_setup.Tickets.TicketMaster import TicketMaster
from caen_setup.Tickets.Tickets import GetParams_Ticket

from caen_tools.connection.client import SyncClient
from caen_tools.MonitorService.monclass import MonitorDB


def ticket_sender(
    connect_addr: str,
    refreshtime: float,
    identity: str,
    logger: logging.Logger,
    device_identity: str,
    dbpath: str,
    receive_time: Optional[int] = None,
):
    """Daemon background function to send GetParams tickets per interval"""
    cli = SyncClient(connect_addr, receive_time=receive_time, identity=identity)
    mondb = MonitorDB(dbpath, logger)
    tkt_json = TicketMaster.serialize(GetParams_Ticket({}))
    # print('TICKET', tkt_json)

    logger.info("Background ticket sender is started")
    logger.debug("Ticket: %s", tkt_json)

    while True:
        logging.debug("Send GetParams ticket")
        try:
            response = cli.query(tkt_json, device_identity)
            mondb.store_data(response)
        except zmq.error.Again:
            logger.warning("No response")

        time.sleep(refreshtime)
