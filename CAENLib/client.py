import zmq
from zmq import MessageTracker


class Client:
    def __init__(self, connect_addr: str):
        # zmq.COPY_THRESHOLD = 0 # need to ensure copy=False messages
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(connect_addr)
        print("Socket HWM", self.socket.get_hwm())  # = 1

    def query(self, obj):
        self.socket.send_json(obj)

        response = self.socket.recv_json()
        return response
