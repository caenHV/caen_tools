import zmq
import zmq.asyncio
from zmq.utils import jsonapi


class AsyncClient:
    """
    Parameters
    ----------
    connect_addr: str
        connection address (e.g. "tcp://localhost:5000")
    receive_time: int | None
        waiting time for server answer (in seconds)
    """

    def __init__(self, connect_addr: str, receive_time: int | None = None):
        # zmq.COPY_THRESHOLD = 0 # need to ensure copy=False messages
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(connect_addr)
        # self.socket.setsockopt(zmq.LINGER, 0)
        if receive_time:
            self.socket.setsockopt(zmq.RCVTIMEO, receive_time * 1000)
        print("Socket HWM", self.socket.get_hwm())  # = 1

    async def query(self, jsobj):
        obj = jsonapi.dumps(jsobj)
        await self.socket.send(obj)

        response = await self.socket.recv()
        responsejs = jsonapi.loads(response)
        return responsejs

    def __del__(self):
        self.socket.close()
        self.context.term()


class Client:
    """
    Parameters
    ----------
    connect_addr: str
        connection address (e.g. "tcp://localhost:5000")
    receive_time: int | None
        waiting time for server answer (in seconds)
    """

    def __init__(self, connect_addr: str, receive_time: int | None = None):
        # zmq.COPY_THRESHOLD = 0 # need to ensure copy=False messages
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(connect_addr)
        # self.socket.setsockopt(zmq.LINGER, 0)
        if receive_time:
            self.socket.setsockopt(zmq.RCVTIMEO, receive_time * 1000)
        print("Socket HWM", self.socket.get_hwm())  # = 1

    def query(self, obj):
        self.socket.send_json(obj)

        response = self.socket.recv_json()
        return response

    def __del__(self):
        self.socket.close()
        self.context.term()
