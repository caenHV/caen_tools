from typing import Optional, Tuple
import zmq

from caen_tools.utils.utils import address_encoder


class DeviceBackendServer:
    """Implementation of the server (zmq.DEALER) of DeviceBackend
    (this one receives data from outer space and interacts with the device)

    Parameters
    ----------
    connect_addr: str
        address for connection (or binding if contain *)
        examples:
            "tcp://localhost:5560" to connect 5560 port
            "tcp://*:5560" to bind 5560 port
    identity: str | None
        socket identity (default is None)
    """

    def __init__(self, connect_addr: str, identity: Optional[str] = None):
        self.context = zmq.Context()
        self.__configure_context()

        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, address_encoder(identity))
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

    def recv(self) -> Tuple[bytes, str]:
        """Recieves data

        Returns
        -------
        Tuple[bytes, str]
            address and message
        """

        address_obj, data_obj = list(self.socket.recv_multipart())
        return (address_obj, data_obj.decode("utf8"))

    def send(self, data: str, address: bytes) -> None:
        """Sends data string on the address

        Parameters
        ----------
        data : str
            message string
        address : bytes
            address to send
        """
        return self.socket.send_multipart([address, data.encode("utf8")])
