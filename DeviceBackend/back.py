import time
import zmq
from zmq.utils import jsonapi
from CAENLib.tickets import Tickets


class Handler:
    def __init__(self):
        self.handler = 10


handler = Handler()


def main():
    context = zmq.Context()
    socket = context.socket(zmq.ROUTER)
    socket.setsockopt(zmq.RCVHWM, 1)
    # socket.connect("tcp://localhost:5560")

    socket.bind("tcp://*:5559")
    print("ROUTER Socket HWM", socket.get_hwm())

    while True:
        data = socket.recv_multipart()
        print("SRV received", data)
        addr, _, tkt_bytes = data
        tkt_json = jsonapi.loads(tkt_bytes)

        print(addr, tkt_json)
        tkt_obj = Tickets.deserialize(tkt_json)

        print(f"Recieved {tkt_obj}... ", end="")
        # status = tkt_obj.execute(handler)
        status = tkt_obj.execute(handler)
        time.sleep(5)

        status_bytes = jsonapi.dumps(status)
        socket.send_multipart([addr, b"", status_bytes])
        print(f"and send status {status} back")


if __name__ == "__main__":
    main()
