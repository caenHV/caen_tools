from functools import wraps
from typing import List

import logging
import subprocess

from fastapi import HTTPException
from caen_tools.utils.receipt import ReceiptResponseError


def response_provider(func):
    """Decorator to raise HTTP error codes
    on ReceiptResponseError instances"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        resp = await func(*args, **kwargs)
        if isinstance(resp.response, ReceiptResponseError) or (
            resp.response.statuscode > 300
        ):
            data = resp.response
            raise HTTPException(status_code=data.statuscode, detail=data.body)
        return resp

    return wrapper


def send_mail(addresses: List[str], subject: str, text: str) -> int:
    """Sends mail to a number of addresses

    Parameters
    ----------
    addresses: List[str]
        set of recipients
    subject: str
        subject of the letter
    text: str
        message

    Notes
    -----
    * for work need mail command in linux

    """

    body_str_encoded_to_byte = text.encode()
    addresses = list(map(lambda x: x.strip(), addresses))
    if len(addresses) == 0:
        return 0

    logging.debug("Start sending mails to %s", addresses)
    return_stat = subprocess.run(
        ["mail", f"-s {subject}"] + addresses,
        input=body_str_encoded_to_byte,
        check=False,
    )
    logging.debug("Sent mail with status code %s", return_stat)
    return 1
