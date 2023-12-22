import argparse
import configparser
import time

from caen_tools.MonitorService.monclass import Monitor


def config_processor(configfile):
    settings = configparser.ConfigParser()
    if configfile is not None:
        settings.read(configfile.name)
    return settings


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

    addr = settings.get("proxy", "address", fallback="tcp://localhost:5559")
    dbpath = settings.get("monitor", "dbpath", fallback="./monitor.db")
    refreshtime = settings.get("monitor", "refreshtime", fallback=60)

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
