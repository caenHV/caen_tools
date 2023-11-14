import zmq


class DeviceBackendServer:
    """Implementation of the server (zmq.REP) of DeviceBackend
    (this one receives data from outer space and interacts with the device)

    Parameters
    ----------
    connect_addr: str
        address for connection (or binding if contain *)
        examples:
            "tcp://localhost:5560" to connect 5560 port
            "tcp://*:5560" to bind 5560 port
    """

    def __init__(self, connect_addr: str):
        self.context = zmq.Context()
        self.__configure_context()

        self.socket = self.context.socket(zmq.REP)
        self.connect_addr = connect_addr
        if "*" in connect_addr:
            self.socket.bind(connect_addr)
        else:
            self.socket.connect(connect_addr)

    def __configure_context(self):
        self.context.setsockopt(zmq.RCVHWM, 1)

    def __del__(self):
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.close()
        self.context.term()

    def recv_json(self) -> list:
        return self.socket.recv_json()

    def send_json(self, data) -> None:
        return self.socket.send_json(data)
