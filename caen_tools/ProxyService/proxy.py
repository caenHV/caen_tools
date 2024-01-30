import argparse
import logging
from typing import Optional
import zmq

from caen_tools.utils.utils import config_processor, get_default_logger


def proxy(
    input_port: int,
    output_port: int,
    monitor_port: int,
    protocol: str = "tcp",
    logger: Optional[logging.Logger] = None,
):
    """Proxy implementation

    Parameters
    ----------
    input_port : int
        input ROUTER port
    output_port : int
        output ROUTER port
    monitor_port : int
        monitor PUB port
    protocol : str
        connection protocol (default is "tcp")
    logger : Optional[Logger]
        used logger
    """

    if logger is None:
        logger = get_default_logger(logging.DEBUG)

    def get_addr(proto, port):
        return f"{proto}://*:{port}"

    in_addr = get_addr(protocol, input_port)
    out_addr = get_addr(protocol, output_port)
    mon_addr = get_addr(protocol, monitor_port)

    in_socket, out_socket = zmq.ROUTER, zmq.ROUTER

    logger.info("Starting proxy, in %s, out %s", in_addr, out_addr)

    context = zmq.Context()
    frontend = context.socket(in_socket)
    backend = context.socket(out_socket)
    frontend.bind(in_addr)
    backend.bind(out_addr)

    # Initialize poll set
    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend, zmq.POLLIN)

    # Switch messages between sockets
    try:
        while True:
            socks = dict(poller.poll())

            if socks.get(frontend) == zmq.POLLIN:
                from_path, out_path, body = list(frontend.recv_multipart())

                out_message = [out_path, from_path, body]
                logger.debug("> FRONTEND > %s, %s, %s", out_path, from_path, body)
                backend.send_multipart(out_message)

            if socks.get(backend) == zmq.POLLIN:
                from_path, out_path, body = list(backend.recv_multipart())

                out_message = [out_path, from_path, body]
                logger.debug(">  BACKEND > %s, %s, %s", out_path, from_path, body)
                frontend.send_multipart(out_message)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt")
    finally:
        frontend.close()
        backend.close()
        context.term()

    # mondev = MonitoredQueue(in_socket, out_socket, zmq.PUB)
    # mondev.bind_in(in_addr)
    # mondev.bind_out(out_addr)
    # mondev.bind_mon(mon_addr)

    # try:
    #     mondev.start()
    # except KeyboardInterrupt:
    #     logger.info("Keyboard interrupt")

    return


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
