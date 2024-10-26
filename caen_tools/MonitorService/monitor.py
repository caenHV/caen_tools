"""Monitor microservice entry point"""

import logging
import multiprocessing as mp

from caen_tools.utils.utils import argparser, config_processor, get_logging_config
from caen_tools.MonitorService.utils import graceful_shutdown
from .api import server
from .worker import worker

CONFIG_SECTION = "monitor"


def main():
    """Monitor microservice entry point"""

    console_args = argparser("Monitor microservice")
    settings = config_processor(console_args.config)

    get_logging_config(
        level=settings.get(CONFIG_SECTION, "loglevel"),
        filepath=settings.get(CONFIG_SECTION, "logfile"),
    )

    logging.info(
        "Start Monitor with arguments %s", dict(settings.items(CONFIG_SECTION))
    )

    worker_process = mp.Process(
        target=worker,
        args=(
            settings.get(CONFIG_SECTION, "device_backend"),
            settings.get(CONFIG_SECTION, "monitor"),
            settings.getfloat(CONFIG_SECTION, "update_period"),
        ),
    )
    server_process = mp.Process(
        target=server,
        args=(
            settings.get(CONFIG_SECTION, "address"),
            settings.get(CONFIG_SECTION, "dbpath"),
            settings.get(CONFIG_SECTION, "param_file_path"),
            settings.get(CONFIG_SECTION, "status_file_path"),
        ),
        daemon=True,
    )

    try:
        worker_process.start()
        server_process.start()
        worker_process.join()
        server_process.join()
    except KeyboardInterrupt:
        logging.info("Shutdown due to keyboard interrupt")
    finally:
        graceful_shutdown([worker_process, server_process], 2, 10)

    return


if __name__ == "__main__":
    main()
