import argparse
from caen_setup import Handler

from caen_setup.Tickets.TicketMaster import TicketMaster
from caen_tools.connection.server import DeviceBackendServer
from caen_tools.utils.utils import config_processor


def device_back(proxy_address: str, map_config: str):
    """Device backend

    Parameters
    ----------
    proxy_address : str
        proxy address to connect device backend
    map_config : str
        file path to layer map
    """

    handler = Handler(map_config, dev_mode=True)
    dbs = DeviceBackendServer(proxy_address)
    # print("ROUTER Socket HWM", socket.get_hwm())

    while True:
        tkt_json = dbs.recv_json_str()
        print(tkt_json)

        tkt_obj = TicketMaster.deserialize(tkt_json)
        print(f"Recieved {tkt_obj}... ", end="")
        status = tkt_obj.execute(handler)
        print(f"and send status {status} back")
        dbs.send_json(status)


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
    try:
        device_back(proxy_address, map_config)
    except KeyboardInterrupt:
        print("keyboard interrupt")
    return


if __name__ == "__main__":
    main()
