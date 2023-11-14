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
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.RCVHWM, 1)
    socket.connect("tcp://localhost:5560")

    # socket.bind("tcp://*:5559")
    print("ROUTER Socket HWM", socket.get_hwm())

    while True:
        data = socket.recv_multipart()
        print("SRV received", data)
        tkt_bytes = data[-1]
        tkt_json = jsonapi.loads(tkt_bytes)
        # tkt_json = socket.recv_json()

        # print(addr, tkt_json)
        tkt_obj = Tickets.deserialize(tkt_json)

        print(f"Recieved {tkt_obj}... ", end="")
        # status = tkt_obj.execute(handler)
        status = tkt_obj.execute(handler)
        time.sleep(5)

        # socket.send_json(status)
        statusd = data
        statusd[-1] = jsonapi.dumps(status)
        socket.send_multipart(statusd)
        print(f"and send status {status} back")


if __name__ == "__main__":
    main()
