from abc import ABC
import json
import zmq
import zmq.asyncio
from zmq.utils import jsonapi
from caen_tools.utils.receipt import (
    Receipt,
    ReceiptJSONDecoder,
    ReceiptJSONEncoder,
    ReceiptResponse,
)


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
    connect_addr: str
        connection address (e.g. "tcp://localhost:5000")
    receive_time: int | None
        waiting time for server answer (in seconds)
    """

    def __init__(self, connect_addr: str, receive_time: int | None = None):
        context = zmq.asyncio.Context()
        self.socket = context.socket(zmq.DEALER)
        self.connect_addr = connect_addr
        super().__init__(context, int(receive_time))

    async def query(self, receipt: Receipt) -> Receipt:
        """Query and response"""

        receipt_str = json.dumps(receipt, cls=ReceiptJSONEncoder).encode("utf-8")
        s = self.context.socket(zmq.DEALER)
        # TODO need protection from ddos

        with s.connect(self.connect_addr) as sock:
            await sock.send_multipart([b"", receipt_str])

            try:
                response = await sock.recv_multipart()
            except zmq.error.Again:
                receipt.response = ReceiptResponse(
                    statuscode=-1, body={"status": "no response"}
                )
                return receipt

            responsejs = jsonapi.loads(response[1])

        s.setsockopt(zmq.LINGER, 0)
        s.close()

        return responsejs
