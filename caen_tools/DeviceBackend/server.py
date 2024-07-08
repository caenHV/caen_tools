from typing import Tuple
import json

import zmq.asyncio
from caen_tools.utils.receipt import Receipt, ReceiptJSONDecoder, ReceiptJSONEncoder


class DeviceBackendServer:
    """Implementation of the async server (zmq.ROUTER) of DeviceBackend
    (this one receives data from outer space and interacts with the device)

    Parameters
    ----------
    connect_addr: str
        address for connection (or binding if contain *)
        examples:
            "tcp://localhost:5560" to connect 5560 port
            "tcp://*:5560" to bind 5560 port
    identity: str
        identity name of the socket (default is 'deviceback')
    """

    def __init__(self, connect_addr: str, identity: str = "deviceback"):
        self.context = zmq.asyncio.Context()
        self.__configure_context()

        self.socket = self.context.socket(zmq.ROUTER)
        self.connect_addr = connect_addr
        self.socket.setsockopt_string(zmq.IDENTITY, identity)
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

    async def recv_receipt(self) -> Tuple[bytes, Receipt]:
        """Gets a receipt from the socket"""
        client, _, receipt_str = await self.socket.recv_multipart()

        receipt = json.loads(receipt_str.decode("utf-8"), cls=ReceiptJSONDecoder)
        return (client, receipt)

    async def send_receipt(self, address: bytes, receipt: Receipt) -> None:
        """Sends a status back"""
        separator = b""
        receipt_str = json.dumps(receipt, cls=ReceiptJSONEncoder).encode("utf-8")
        await self.socket.send_multipart([address, separator, receipt_str])
        return
