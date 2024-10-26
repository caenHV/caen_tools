"""A set of utility functions for Monitor microservice"""

from signal import SIGINT
from time import time, sleep

import logging
import os


def graceful_shutdown(processes: list, grace_period: int = 2, kill_period: int = 10):
    """Graceful shutdowns multiprocess program

    Parameters
    ----------
    processes: list
        list of processes to shutdown
    grace_period: int, default 2 (seconds)
        send SIGINT after this time (if process is not shutdowned)
    kill_period: int, default 10 (seconds)
        send SIGKILL after this time (if process is not shutdowned)
    """

    t = time()
    while alive_procs := [p for p in processes if p.is_alive()]:
        if time() > t + grace_period:
            for p in alive_procs:
                os.kill(p.pid, SIGINT)
                logging.warning("Sending SIGINT to %s", p)
        elif time() > t + kill_period:
            for p in alive_procs:
                p.kill()
                logging.warning("Sending SIGKILL to %s", p)
        sleep(0.05)
    return
