from functools import wraps
from fastapi import HTTPException

from caen_tools.utils.receipt import ReceiptResponseError


def response_provider(func):
    """Decorator to raise HTTP error codes
    on ReceiptResponseError instances"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        resp = await func(*args, **kwargs)
        if isinstance(resp.response, ReceiptResponseError):
            data = resp.response
            raise HTTPException(status_code=data.statuscode, detail=data.body)
        return resp

    return wrapper
