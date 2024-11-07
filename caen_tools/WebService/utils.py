from functools import wraps
from typing import List
from email.message import EmailMessage

import asyncio
import json
import logging
import smtplib
import subprocess

from fastapi import HTTPException
from caen_tools.utils.receipt import ReceiptResponseError
from caen_tools.utils.receipt import ReceiptJSONEncoder


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
    * for work need mail smtp server

    """

    message = EmailMessage()
    message.set_content(text)
    message["Subject"] = subject
    message["From"] = "notify@caendc.cmd"
    message["To"] = ", ".join(addresses)

    if len(addresses) == 0:
        return 0

    logging.debug("Start sending mails to %s", addresses)
    smtp_server = smtplib.SMTP("172.17.0.1:25")
    smtp_server.send_message(message)
    smtp_server.quit()
    logging.debug("Sent mail")
    return 1


def broadcaster(delay, function, *args, **kwargs):
    """Creates a generator to broadcast `function`
    function responses every delay (in seconds) in the loop"""

    async def generator():
        """yields response strings"""
        try:
            while True:
                response = await function(*args, **kwargs)
                response_str = json.dumps(response, cls=ReceiptJSONEncoder)
                yield response_str
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logging.info("Disconnected from client (via refresh/close)")

    return generator()
