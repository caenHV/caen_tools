from functools import wraps
from typing import List
from fastapi import HTTPException

import logging
import subprocess
import socket
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

def send_UDP_to_MChS_Controller(UDP_IP: str, UDP_PORT: str, client_id: str, ack: bool):
    """Sends UDP datagram to the MChS Controller.
    For details read this: https://cmd.inp.nsk.su/wiki/pub/CMD3/Diplom2018/Зубакин_АС.pdf

    Parameters
    ----------
    UDP_IP : str
        MChS controller host address
    UDP_PORT : str
        Port listened by MChS controller 
    client_id : str
        Id of Caen_HV registered in MChS controller
    ack : bool
        True == everything is ok, False == lock Triggers
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.debug("Opened send_UDP_to_MChS_Controller socket. Start sending UDP package to MChS Controller.")
    
    try:
        UDP_PORT = int(UDP_PORT) # type: ignore
        sock.sendto(str.encode(f"{'ACK' if ack else 'NACK'} {client_id}"), (UDP_IP, UDP_PORT))
        logging.info("Sent UDP package to MChS Controller with status code %s", ('ACK' if ack else 'NACK'))
    except ValueError as e:
        logging.error("Wrong MChS_Controler info in config.ini: %s", e)
        
    sock.close()
    logging.debug("Closed send_UDP_to_MChS_Controller socket.")
    
    return
