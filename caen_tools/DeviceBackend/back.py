import argparse
import logging
import traceback
from caen_setup import Handler

from caen_setup.Tickets.TicketMaster import TicketMaster
from caen_tools.connection.server import DeviceBackendServer
from caen_tools.utils.utils import config_processor, get_default_logger


def device_back(proxy_address: str, map_config: str, identity: str, logger=None):
    """Device backend

    Parameters
    ----------
    proxy_address : str
        proxy address to connect device backend
    map_config : str
        file path to layer map
    identity : str
        socket name
    logger : logging.Logger
    """

    if logger is None:
        logger = get_default_logger(logging.DEBUG)

    logger.info("Start Device Backend")
    handler = Handler(map_config, dev_mode=True)
    dbs = DeviceBackendServer(proxy_address, identity)
    # print("ROUTER Socket HWM", socket.get_hwm())

    try:
        while True:
            address_obj, tkt_json = dbs.recv()
            tkt_obj = TicketMaster.deserialize(tkt_json)
            logger.info("Accepted ticket %s from address %s", tkt_json, address_obj)

            status = tkt_obj.execute(handler)
            logger.debug("The ticket has beed executed")

            dbs.send(status, address_obj)
            logger.info("Responsed back %s", status)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt")
    except BaseException:
        logger.error(traceback.format_exc())
    finally:
        del dbs
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
    proxy_address = settings.get("device", "proxy_address")
    map_config = settings.get("device", "map_config")
    identity = settings.get("device", "identity")

    device_back(proxy_address, map_config, identity)
    return


if __name__ == "__main__":
    main()
