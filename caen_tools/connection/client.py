from abc import ABC
import zmq
import zmq.asyncio
from zmq.utils import jsonapi

from caen_tools.utils.utils import address_encoder


class BaseClient(ABC):
    """Abstract parent for (sync and async) client classes"""

    def __init__(self, context, socket_type, receive_time=None, identity=None):
        self.context = context
        self.recv_time = receive_time
        self.identity = identity
        self.socket = self.context.socket(socket_type)
        self.__configure_context()

    def __configure_context(self):
        self.context.setsockopt(zmq.SNDTIMEO, 1000)
        self.context.setsockopt(zmq.SNDHWM, 1000)
        self.context.setsockopt(zmq.LINGER, 0)
        if self.recv_time:
            self.socket.setsockopt(zmq.RCVTIMEO, self.recv_time * 1000)
        if self.identity:
            self.socket.setsockopt(zmq.IDENTITY, address_encoder(self.identity))

    def __del__(self):
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.close()
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
        self.connect_addr = connect_addr
        super().__init__(context, zmq.DEALER, receive_time)

    async def query(self, jsobj, address=None):
        """
        Parameters
        ----------
        jsobj : str
            json string as message
        address : str
            address for query
        """
        obj = jsonapi.dumps(jsobj)

        with self.socket.connect(self.connect_addr) as sock:
            # await sock.send_multipart([b"", obj])
            await sock.send_multipart([address_encoder(address), obj])

            try:
                # response_proxy = await self.socket.recv_multipart()
                # print(f"Proxy response {response_proxy}")
                response = await sock.recv_multipart()
            except zmq.error.Again:
                return {"status": "no response"}

            responsejs = jsonapi.loads(response[1])

        return responsejs


class SyncClient(BaseClient):
    """Sync client class implementation (for ConsoleClient and so on)

    Parameters
    ----------
    connect_addr: str
        connection address (e.g. "tcp://localhost:5000")
    receive_time: int | None
        waiting time for server answer (in seconds)
    """

    def __init__(
        self,
        connect_addr: str,
        receive_time: int | None = None,
        identity: str | None = None,
    ):
        context = zmq.Context()
        self.connect_addr = connect_addr
        super().__init__(context, zmq.DEALER, receive_time, identity)

    def query(self, jsobj: str, address: str) -> object:
        # obj = jsonapi.dumps(jsobj)
        obj = address_encoder(jsobj)
        address_obj = address_encoder(address)

        with self.socket.connect(self.connect_addr) as sock:
            # sock.send_multipart([b"", obj])

            print("socket multi", [address_obj, obj])
            sock.send_multipart([address_obj, obj])

            # response_proxy = self.socket.recv_multipart()
            # print(f"Proxy response {response_proxy}")

            response: list = sock.recv_multipart()
            responsejs = jsonapi.loads(response[1])
        return responsejs
