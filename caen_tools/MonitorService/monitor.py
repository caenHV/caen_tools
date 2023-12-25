import argparse
import time

from caen_tools.MonitorService.monclass import Monitor
from caen_tools.utils.utils import config_processor


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

    addr = settings.get("monitor", "proxy_address")
    dbpath = settings.get("monitor", "dbpath")
    refreshtime = int(settings.get("monitor", "refreshtime"))

    m = Monitor(dbpath, addr)
    m.add_row()
    while True:
        m.add_row()
        time.sleep(refreshtime)
    return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
