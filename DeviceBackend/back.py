import time
import zmq
from CAENLib.tickets import Tickets


class Handler:
    def __init__(self):
        self.handler = 10


def main():
    handler = Handler()
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    # socket.connect("tcp://localhost:5560")

    socket.bind("tcp://*:5559")
    print("REP Socket HWM", socket.get_hwm())

    while True:
        tkt_json = socket.recv_json()
        tkt_obj = Tickets.deserialize(tkt_json)

        print(f"Recieved {tkt_obj}... ", end="")
        status = tkt_obj.execute(handler)

        time.sleep(5)

        socket.send_json(status)
        print(f"and send status {status} back")


if __name__ == "__main__":
    main()
