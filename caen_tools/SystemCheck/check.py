from time import sleep, time
import argparse
import logging
import signal
import os
import multiprocessing as mp

from caen_tools.SystemCheck.server import run_server
from caen_tools.SystemCheck.worker import run_worker
from caen_tools.utils.utils import config_processor, get_logging_config

CONFIG_SECTION = "check"


def main():
    """Prepares configuration and launches necessary functions"""

    parser = argparse.ArgumentParser(description="SysCheck microservice")
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        type=argparse.FileType("r"),
        help="Config file",
        nargs="?",
    )
    args = parser.parse_args()
    settings = config_processor(args.config)
    address = settings.get(CONFIG_SECTION, "address")

    get_logging_config(
        level=settings.get(CONFIG_SECTION, "loglevel"),
        filepath=settings.get(CONFIG_SECTION, "logfile"),
    )

    logging.info(
        "Start SysCheck with arguments %s", dict(settings.items(CONFIG_SECTION))
    )

    mchs_dict = dict(
        udp_ip=settings.get(CONFIG_SECTION, "mchs_host"),
        udp_port=settings.get(CONFIG_SECTION, "mchs_port"),
        client_id=settings.get(CONFIG_SECTION, "mchs_client_id"),
    )

    manager = mp.Manager()
    shared_parameters = manager.dict(
        interlock=manager.dict(
            enable=settings.getboolean(CONFIG_SECTION, "interlock_follow"),
            repeat_every=60,
            last_check=0,
            voltage_modifier=settings.getfloat(
                CONFIG_SECTION, "interlock_voltage_modifier"
            ),
            mchs=mchs_dict,
        ),
        health=manager.dict(
            enable=True,
            repeat_every=1,
            last_check=0,
            mchs=mchs_dict,
        ),
    )

    worker = mp.Process(
        target=run_worker,
        args=(
            shared_parameters,
            settings.get(CONFIG_SECTION, "device_backend"),
            settings.get(CONFIG_SECTION, "monitor"),
            settings.get(CONFIG_SECTION, "interlock_db_uri"),
        ),
    )
    serv = mp.Process(
        target=run_server,
        args=(shared_parameters, address, CONFIG_SECTION),
        daemon=True,
    )

    try:
        worker.start()
        serv.start()
        worker.join()
        serv.join()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt")
        logging.info("SHARMEM %s", shared_parameters)
    finally:
        # Graceful shutdown
        grace_period = 2  # in seconds
        kill_period = 10
        t = time()
        while alive_procs := [p for p in [worker, serv] if p.is_alive()]:
            if time() > t + grace_period:
                for p in alive_procs:
                    os.kill(p.pid, signal.SIGINT)
                    logging.warning("Sending SIGINT to %s", p)
            elif time() > t + kill_period:
                for p in alive_procs:
                    logging.warning("Sending SIGKILL to %s", p)
                    p.kill()
            sleep(0.05)

    return


if __name__ == "__main__":
    main()
