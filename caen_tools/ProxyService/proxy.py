import zmq
from zmq.devices import MonitoredQueue


def main():
    """Proxy implementation"""

    in_addr = "tcp://*:5559"
    out_addr = "tcp://*:5560"
    mon_addr = "tcp://*:5561"

    mondev = MonitoredQueue(zmq.ROUTER, zmq.DEALER, zmq.PUB)
    mondev.bind_in(in_addr)
    mondev.bind_out(out_addr)
    mondev.bind_mon(mon_addr)

    mondev.start()


if __name__ == "__main__":
    main()
