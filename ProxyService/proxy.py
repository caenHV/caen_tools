import zmq
from zmq.devices import MonitoredQueue


def main():
    in_addr = "tcp://*:5559"
    out_addr = "tcp://*:5560"
    # mon_addr = "tcp://*:5561"

    # mondev = MonitoredQueue(zmq.ROUTER, zmq.DEALER, zmq.PUB)
    # mondev.bind_in(in_addr)
    # mondev.bind_out(out_addr)
    # mondev.bind_mon(mon_addr)

    # mondev.start()

    context = zmq.Context()
    frontend = context.socket(zmq.ROUTER)
    backend = context.socket(zmq.DEALER)
    frontend.bind(in_addr)
    backend.bind(out_addr)

    # Initialize poll set
    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend, zmq.POLLIN)

    # Switch messages between sockets
    while True:
        try:
            socks = dict(poller.poll())
        except KeyboardInterrupt:
            break

        if socks.get(frontend) == zmq.POLLIN:
            message = frontend.recv_multipart()
            frontend.send_multipart(message)
            print(f"PROXY: RCV -> message {message}")
            backend.send_multipart(message)

        if socks.get(backend) == zmq.POLLIN:
            message = backend.recv_multipart()
            print(f"PROXY: RCV <- message {message}")
            frontend.send_multipart(message)

    frontend.close()
    backend.close()
    context.term()

if __name__ == "__main__":
    main()
