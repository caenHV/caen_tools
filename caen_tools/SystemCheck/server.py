"""Managers a server for system check microservice"""

import asyncio
import logging

from caen_tools.connection.server import RouterServer
from caen_tools.SystemCheck.api import APIFactory

NUM_ASYNC_TASKS = 5
sem = asyncio.Semaphore(NUM_ASYNC_TASKS)


async def process_message(srv: RouterServer, shared_parameters: dict) -> None:
    """Waits a message, processes it and sends back a response

    Parameters
    ----------
    dbs : RouterServer
        server instance
    shared_parameters : dict
        dictionary with shared parameters for worker usage
    """

    async with sem:
        asyncio.ensure_future(process_message(srv, shared_parameters))

        client_address, receipt = await srv.recv_receipt()
        logging.info("Received %s from %s", receipt, client_address)

        response = APIFactory.execute_receipt(receipt, shared_parameters)
        await srv.send_receipt(client_address, response)
        logging.info("send response to client %s", client_address)

    return


def run_server(
    shared_parameters: dict, address: str, identity: str = "syscheck"
) -> None:
    """Runs a server

    Parameters
    ----------
    shared_parameters: dict
        shared memory to keep parameters for worker
    address: str
        binding address for the server instance
    identity: str, default "syscheck"
        server identity name
    """

    logging.info("Start server")

    srv = RouterServer(address, identity)
    loop = asyncio.get_event_loop()

    try:
        asyncio.ensure_future(process_message(srv, shared_parameters))
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Finish the server")
    finally:
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
            logging.debug("Close task %s", task)
        logging.info("Final server close")

    return
