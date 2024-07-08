import asyncio
import argparse
import random
from caen_setup import Handler

# from caen_setup.Tickets.TicketMaster import TicketMaster
from caen_tools.DeviceBackend.server import DeviceBackendServer
from caen_tools.DeviceBackend.apifactory import APIFactory
from caen_tools.utils.utils import config_processor

NUM_ASYNC_TASKS = 5
sem = asyncio.Semaphore(NUM_ASYNC_TASKS)


async def process_message(dbs: DeviceBackendServer, handler: Handler) -> None:
    """Processes one input message"""

    async with sem:
        asyncio.ensure_future(process_message(dbs, handler))

        client_address, receipt = await dbs.recv_receipt()
        print("Received", receipt, "from", client_address)
        stime = random.randint(1, 3)
        print("sleep", stime)
        await asyncio.sleep(stime)
        print("Finish sleep")
        out_receipt = APIFactory.execute_receipt(receipt, handler)
        await dbs.send_receipt(client_address, out_receipt)
        print("and send back")

    return


# https://stackoverflow.com/questions/44982332/asyncio-await-and-infinite-loops
# https://stackoverflow.com/questions/47745989/how-to-concurrently-run-a-infinite-loop-with-asyncio


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

    dbs = DeviceBackendServer(address)
    handler = Handler(map_config, dev_mode=True)
    # print("ROUTER Socket HWM", socket.get_hwm())

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
