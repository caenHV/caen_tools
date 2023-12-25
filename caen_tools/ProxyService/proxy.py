import argparse
import zmq
from zmq.devices import MonitoredQueue

from caen_tools.utils.utils import config_processor


def proxy(input_port: int, output_port: int, monitor_port: int, protocol: str = "tcp"):
    """Proxy implementation

    Parameters
    ----------
    input_port : int
        input ROUTER port
    output_port : int
        output DEALER port
    monitor_port : int
        monitor PUB port
    protocol : str
        connection protocol (default is "tcp")
    """

    def get_addr(proto, port):
        return f"{proto}://*:{port}"

    in_addr = get_addr(protocol, input_port)
    out_addr = get_addr(protocol, output_port)
    mon_addr = get_addr(protocol, monitor_port)

    mondev = MonitoredQueue(zmq.ROUTER, zmq.DEALER, zmq.PUB)
    mondev.bind_in(in_addr)
    mondev.bind_out(out_addr)
    mondev.bind_mon(mon_addr)

    mondev.start()


def main():
    parser = argparse.ArgumentParser(description="Proxy microservice")
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
    input_port = settings.get("proxy", "input_port")
    output_port = settings.get("proxy", "output_port")
    monitor_port = settings.get("proxy", "monitor_port")
    protocol = settings.get("proxy", "protocol")
    proxy(input_port, output_port, monitor_port, protocol)


if __name__ == "__main__":
    main()
