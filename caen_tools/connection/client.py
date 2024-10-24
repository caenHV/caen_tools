"""Base zmq client implementation"""

from abc import ABC
from typing import Dict
import json
import logging
import zmq
import zmq.asyncio

from caen_tools.utils.receipt import Receipt, ReceiptJSONEncoder, ReceiptJSONDecoder
from caen_tools.utils.resperrs import RResponseErrors


class BaseClient(ABC):
    """Abstract parent for (sync and async) client classes"""

    def __init__(self, context, receive_time=None):
        self.context = context
        self.recv_time = receive_time
        self.__configure_context()

    def __configure_context(self):
        self.context.setsockopt(zmq.SNDTIMEO, 1000)
        self.context.setsockopt(zmq.SNDHWM, 1000)
        self.context.setsockopt(zmq.LINGER, 0)
        if self.recv_time:
            self.context.setsockopt(zmq.RCVTIMEO, self.recv_time * 1000)

    def __del__(self):
        self.context.term()


class AsyncClient(BaseClient):
    """Async client class implementation (for WebService and so on)

    Parameters
    ----------
    connect_addr: Dict[str, str]
        map of connection addresses in format {"identity" : "address"}
        (e.g. {"device_backend", "tcp://localhost:5000"})
    receive_time: int, default 20
        waiting time for server answer (in seconds)
    """

    def __init__(self, connect_addresses: Dict[str, str], receive_time: int = 20):
        logging.debug("Start AsyncCli initialization")
        context = zmq.asyncio.Context()
        self.socket = context.socket(zmq.DEALER)
        self.connect_addresses = connect_addresses
        super().__init__(context, int(receive_time))

    async def query(
        self, receipt: Receipt, receive_time: float | None = None
    ) -> Receipt:
        """Query and response

        Parameters
        ----------
        receipt : Receipt
            instruction with full information
            about sender, executor and task

            the field "executor" in the Receipt
            must correspond to the key from the connect_addresses

        receive_time : float | None, None
             waiting answer time for the response from the client (in seconds)

        Returns
        -------
        Receipt
            the same receipt with filled ReceiptResponse block
        """

        if receipt.executor not in self.connect_addresses:
            logging.error("Connect address %s is not allowed", receipt.executor)
            receipt.response = RResponseErrors.NotFound(
                f"Executor {receipt.executor} is not found"
            )
            return receipt

        receipt_str = json.dumps(receipt, cls=ReceiptJSONEncoder).encode("utf-8")
        s = self.context.socket(zmq.DEALER)
        connect_address = self.connect_addresses[receipt.executor]

        if receive_time is not None:
            s.setsockopt(zmq.RCVTIMEO, receive_time * 1000)

        with s.connect(connect_address) as sock:
            await sock.send_multipart([b"", receipt_str])

            try:
                response = await sock.recv_multipart()
                receipt_out = json.loads(
                    response[1].decode("utf-8"), cls=ReceiptJSONDecoder
                )
            except zmq.error.Again:
                logging.warning("No response from executor %s", receipt.executor)
                receipt_out = receipt
                receipt_out.response = RResponseErrors.GatewayTimeout(
                    f"No response from {receipt_out.executor} service"
                )

        s.setsockopt(zmq.LINGER, 0)
        s.close()

        return receipt_out


class AsyncStreamClient(BaseClient):
    """Async client class implementation (for STREAM sockets)

    Parameters
    ----------
    receive_time: int, default 20
        waiting time for server answer (in seconds)
    """

    def __init__(self, receive_time: int = 20):
        logging.debug("Start AsyncStreamCli initialization")
        context = zmq.asyncio.Context()
        super().__init__(context, receive_time)

    async def query(self, connect_address: str, message: bytes) -> list[bytes] | None:
        """Sends a query to some address and receives the answer
        
        Parameters
        ----------
        connect_address: str
            address like: "protocol://host:port"
        message: bytes
            sending message
        
        Returns
        -------
        list[bytes] | None
            answer (None if not connected)
        """

        s = self.context.socket(zmq.STREAM)

        with s.connect(connect_address) as sock:

            id_sock = sock.getsockopt(zmq.IDENTITY)
            await sock.send(id_sock, zmq.SNDMORE)
            await sock.send(message)

            answer = None
            try:
                _ = await sock.recv_multipart()
                answer = await sock.recv_multipart()
                logging.debug("Received answer %s (from %s)", answer, connect_address)
            except zmq.error.Again:
                logging.warning("No response from %s", connect_address, exc_info=True)

        s.setsockopt(zmq.LINGER, 0)
        s.close()

        return answer
