"""Implementation of the DeviceBackend microservice"""

import asyncio
import argparse
import logging
from caen_setup import Handler

from caen_tools.connection.server import RouterServer
from caen_tools.DeviceBackend.apifactory import APIFactory
from caen_tools.utils.utils import config_processor, get_logging_config

NUM_ASYNC_TASKS = 5
sem = asyncio.Semaphore(NUM_ASYNC_TASKS)
logger = logging.getLogger(__file__)


async def process_message(dbs: RouterServer, handler: Handler) -> None:
    """Waits a message, processes it and sends back a response

    Parameters
    ----------
    dbs : RouterServer
        server instance
    handler : Handler
        handler object for CAEN board managing
    """

    async with sem:
        asyncio.ensure_future(process_message(dbs, handler))

        client_address, receipt = await dbs.recv_receipt()
        logging.info("Received %s from %s", receipt, client_address)
        out_receipt = APIFactory.execute_receipt(receipt, handler)
        await dbs.send_receipt(client_address, out_receipt)
        logging.info("send response to client %s", client_address)

    return


def main():
    parser = argparse.ArgumentParser(description="DeviceBackend microservice")
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
    address = settings.get("device", "address")
    map_config = settings.get("device", "map_config")
    fake_board = settings.getboolean("device", "fake_board")
    handler_refresh_time = settings.getint("device", "refersh_time")

    get_logging_config(
        level=settings.get("device", "loglevel"),
        filepath=settings.get("device", "logfile"),
    )
    logging.info(
        "Successfuly started DeviceBackend with arguments %s",
        dict(settings.items("device")),
    )

    dbs = RouterServer(address, "devback")
    handler = Handler(
        map_config, refresh_time=handler_refresh_time, fake_board=fake_board
    )

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(process_message(dbs, handler))
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Finish the program")
    finally:
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
            logging.debug("Close task %s", task)
        logging.info("Final program close")


if __name__ == "__main__":
    main()
