import asyncio
import argparse
from caen_setup import Handler

# from caen_setup.Tickets.TicketMaster import TicketMaster
# from caen_tools.DeviceBackend.server import DeviceBackendServer
from caen_tools.connection.server import RouterServer
from caen_tools.DeviceBackend.apifactory import APIFactory
from caen_tools.utils.utils import config_processor

NUM_ASYNC_TASKS = 5
sem = asyncio.Semaphore(NUM_ASYNC_TASKS)


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
        print("Received", receipt, "from", client_address)
        out_receipt = APIFactory.execute_receipt(receipt, handler)
        await dbs.send_receipt(client_address, out_receipt)
        print("and send back")

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

    dbs = RouterServer(address, "devback")
    handler = Handler(map_config, dev_mode=True)

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(process_message(dbs, handler))
        loop.run_forever()
    except KeyboardInterrupt:
        print("keyboard interrupt")
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == "__main__":
    main()
