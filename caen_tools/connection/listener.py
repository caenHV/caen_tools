import zmq


class Listener:
    """Subscriber implementation for message listening"""

    def __init__(self, connect_addr: str):
        self.connect_addr = connect_addr
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.connect_addr)
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")

    def recv_msg(self):
        response = self.socket.recv_multipart()
        return response

    def __del__(self):
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.close()
        self.context.term()
