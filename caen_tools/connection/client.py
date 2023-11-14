from abc import ABC
import zmq
import zmq.asyncio
from zmq.utils import jsonapi


class BaseClient(ABC):
    """Abstract parent for (sync and async) client classes"""

    def __init__(self, context, socket_type, receive_time=None):
        self.context = context
        self.recv_time = receive_time
        self.socket = self.context.socket(socket_type)
        self.__configure_context()

    def __configure_context(self):
        self.context.setsockopt(zmq.SNDTIMEO, 1000)
        self.context.setsockopt(zmq.SNDHWM, 1000)
        self.context.setsockopt(zmq.LINGER, 0)
        if self.recv_time:
            self.socket.setsockopt(zmq.RCVTIMEO, self.recv_time * 1000)

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

    async def query(self, jsobj):
        obj = jsonapi.dumps(jsobj)

        with self.socket.connect(self.connect_addr) as sock:
            await sock.send_multipart([b"", obj])

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

    def __init__(self, connect_addr: str, receive_time: int | None = None):
        context = zmq.Context()
        self.connect_addr = connect_addr
        super().__init__(context, zmq.DEALER, receive_time)

    def query(self, jsobj):
        obj = jsonapi.dumps(jsobj)

        with self.socket.connect(self.connect_addr) as sock:
            sock.send_multipart([b"", obj])

            # response_proxy = self.socket.recv_multipart()
            # print(f"Proxy response {response_proxy}")

            response: list = sock.recv_multipart()
            responsejs = jsonapi.loads(response[1])
        return responsejs
