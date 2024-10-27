from enum import IntEnum
from typing import TypeAlias
import logging
import zmq
import zmq.asyncio

from caen_tools.utils.receipt import Receipt, ReceiptResponse

Address: TypeAlias = str

class Code:
    """List of API statuscodes"""
    NO_CONNECT = 0,
    OK = 1


class APIMethods:

    EXECUTOR = "interlock"

    @staticmethod
    async def __connect(context: zmq.asyncio.Context, connect_address: Address, message: bytes) -> list[bytes] | None:
        answer = None
        s = context.socket(zmq.STREAM)

        with s.connect(connect_address) as sock:

            id_sock = sock.getsockopt(zmq.IDENTITY)
            await sock.send(id_sock, zmq.SNDMORE)
            await sock.send(message)

            try:
                _ = await sock.recv_multipart()
                answer = await sock.recv_multipart()
                logging.debug("Received answer %s (from %s)", answer, connect_address)
            except zmq.error.Again:
                logging.warning("No response from %s", connect_address, exc_info=True)

        s.setsockopt(zmq.LINGER, 0)
        s.close()
        return answer
    
    @staticmethod
    def _form_receipt(title: str, params: dict) -> Receipt:
        return Receipt(sender="unknown", executor=APIMethods.EXECUTOR, title=title, params=params)
    
    @staticmethod
    def _form_response(code: int, body: dict | str) -> ReceiptResponse:
        return ReceiptResponse(statuscode=code, body=body)
    
    @staticmethod
    async def get_field(context: zmq.asyncio.Context, connect_address: Address, field: str) -> Receipt:
        """Gets a value of the field"""

        get_request = bytes(f"n:{field}|m:get\n", encoding="UTF-8")
        answer = await APIMethods.__connect(context, connect_address, get_request)

        receipt = APIMethods._form_receipt("get_field", dict(
            address=connect_address, field=field,
        ))
        if answer is None:
            receipt.response = APIMethods._form_response(code=Code.NO_CONNECT, body="Connection problem")
            return receipt
        
        

            receipt.response = APIMethods._form_response(code=Code.OK, )
        return receipt

    @staticmethod
    async def set_field(context: zmq.asyncio.Context, connect_address: Address, field: str, value: int) -> Receipt:
        """Sets a value to the field"""

        # TODO implement logic

        receipt = APIMethods._form_receipt("set_field", dict(
            address=connect_address, field=field, value=value,
        ))
        return receipt