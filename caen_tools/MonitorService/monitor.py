"""Monitor microservice"""

import argparse
import asyncio
import json
import logging

from caen_tools.connection.server import RouterServer
from caen_tools.MonitorService.SystemCheck import SystemCheck
from caen_tools.MonitorService.monclass import Monitor
from caen_tools.utils.receipt import Receipt, ReceiptResponse
from caen_tools.utils.utils import config_processor, get_logging_config

NUM_ASYNC_TASKS = 5
sem = asyncio.Semaphore(NUM_ASYNC_TASKS)


async def process_message(dbs: RouterServer, monitor: Monitor) -> None:
    """Processes one input message"""

    async with sem:
        asyncio.ensure_future(process_message(dbs, monitor))

        client_address, receipt = await dbs.recv_receipt()
        logging.info("Received %s from %s", receipt.title, client_address)
        logging.debug("Full receipt %s", receipt)

        out_receipt = APIFactory.execute_receipt(receipt, monitor)

        await dbs.send_receipt(client_address, out_receipt)
        logging.info("send response to client %s", client_address)

    return


def check_receipt(receipt: Receipt) -> bool:
    """Check input receipt"""
    is_executor = receipt.executor.lower() == "monitor"
    return is_executor


class APIMethods:
    """Contains implementations of the API methods
    of the microservice"""

    @staticmethod
    def status(receipt: Receipt, monitor: Monitor):
        """Returns status of the microservice"""
        response = monitor.is_ok()
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0, body={}
        )
        return receipt

    @staticmethod
    def execute_send(receipt: Receipt, monitor: Monitor):
        """Sends device parameters in Monitor.
        Monitor writes them in the DB and returns health report"""
        response = monitor.send_params(
            receipt.params, measurement_time=receipt.timestamp
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body=response["system_health_report"],
        )
        return receipt

    @staticmethod
    def execute_get(receipt: Receipt, monitor: Monitor):
        """Gets device parameters from Monitor"""
        response = monitor.get_params(
            receipt.params["start_time"], receipt.params["end_time"]
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body=(
                response["params"]
                if response["is_ok"]
                else "Something is wrong in the DB. No rows selected."
            ),
        )
        return receipt

    @staticmethod
    def execute_get_interlock(receipt: Receipt, monitor: Monitor):
        """Returns interlock status"""
        response = monitor.get_interlock()
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body=(
                response["system_health_report"]
                if response["is_ok"]
                else "Something is wrong in the DB. No rows selected."
            ),
        )
        return receipt

    @staticmethod
    def wrongroute(receipt: Receipt) -> Receipt:
        """Default answer for the wrong title field in the receipt"""
        receipt.response = ReceiptResponse(
            statuscode=404, body="this api method is not found"
        )
        return receipt


class APIFactory:
    apiroutes = {
        "status": APIMethods.status,
        "send_params": APIMethods.execute_send,
        "get_params": APIMethods.execute_get,
        "get_interlock": APIMethods.execute_get_interlock,
    }

    @staticmethod
    def execute_receipt(receipt: Receipt, monitor: Monitor) -> Receipt:
        """Matches a function to execute input receipt"""

        if receipt.title in APIFactory.apiroutes and check_receipt(receipt):
            return APIFactory.apiroutes[receipt.title](receipt, monitor)
        return APIMethods.wrongroute(receipt)


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

    address = settings.get("monitor", "address")
    dbpath = settings.get("monitor", "dbpath")
    param_file_path = settings.get("monitor", "param_file_path")
    channel_map_path = settings.get("monitor", "channel_map_path")
    interlock_db_uri = settings.get("monitor", "interlock_db_uri")
    with open(channel_map_path, encoding="utf-8") as f:
        channel_map = json.load(f)
    max_interlock_check_delta_time = int(
        settings.get("monitor", "max_interlock_check_delta_time")
    )

    get_logging_config(
        level=settings.get("monitor", "loglevel"),
        filepath=settings.get("monitor", "logfile"),
    )
    logging.info(
        "Successfuly started Monitor with arguments %s",
        dict(settings.items("monitor")),
    )

    system_check = SystemCheck(dbpath, interlock_db_uri, max_interlock_check_delta_time)
    monitor = Monitor(dbpath, system_check, channel_map, param_file_path, interlock_db_uri)

    dbs = RouterServer(address, "monitor")

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(process_message(dbs, monitor))
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
    try:
        main()
    except KeyboardInterrupt:
        pass
