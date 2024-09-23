"""A number of utilty functions"""

import asyncio
import timeit
import logging
import socket


def check_process(repeat_every: float):
    """Decorator to run a check scenario
    every `repeat_every` seconds

    Parameters
    ----------
    repeat_every: float
        time to repeat given scenario, in seconds
    """

    def run_check(checkfoo):
        async def wrapper(*args, **kwargs):
            starttime = timeit.default_timer()
            result = await checkfoo(*args, **kwargs)
            exectime = timeit.default_timer() - starttime
            await asyncio.sleep(max(0, repeat_every - exectime))
            logging.debug("check_process decorator is finished")

            asyncio.create_task(check_process(repeat_every)(checkfoo)(*args, **kwargs))
            return result

        return wrapper

    return run_check


def send_udp_to_mchs_controller(udp_ip: str, udp_port: str, client_id: str, ack: bool):
    """Sends UDP datagram to the MChS Controller.
    For details read this: https://cmd.inp.nsk.su/wiki/pub/CMD3/Diplom2018/Зубакин_АС.pdf

    Parameters
    ----------
    udp_ip : str
        MChS controller host address
    udp_port : str
        Port listened by MChS controller
    client_id : str
        Id of Caen_HV registered in MChS controller
    ack : bool
        True == everything is ok, False == lock Triggers
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.debug(
        "Opened send_UDP_to_MChS_Controller socket. Start sending UDP package to MChS Controller."
    )

    try:
        udp_port = int(udp_port)  # type: ignore
        sock.sendto(
            str.encode(f"{'ACK' if ack else 'NACK'} {client_id}"), (udp_ip, udp_port)
        )
        logging.info(
            "Sent UDP package to MChS Controller with status code %s",
            ("ACK" if ack else "NACK"),
        )
    except ValueError as e:
        logging.error("Wrong MChS_Controler info in config.ini: %s", e)

    sock.close()
    logging.debug("Closed send_UDP_to_MChS_Controller socket.")

    return
