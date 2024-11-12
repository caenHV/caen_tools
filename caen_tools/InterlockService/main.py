"""Interlock microservice entry point"""

import logging

from caen_tools.utils.utils import argparser, config_processor, get_logging_config
from caen_tools.InterlockService.interlock import InterlockProcessor

CONFIG_SECTION = "interlock"


def main():
    """Interlock microservice entry point"""

    console_args = argparser("Interlock microservice")
    settings = config_processor(console_args.config)

    get_logging_config(
        level=settings.get(CONFIG_SECTION, "loglevel"),
        filepath=settings.get(CONFIG_SECTION, "logfile"),
    )

    logging.info(
        "Start Interlock with arguments %s", dict(settings.items(CONFIG_SECTION))
    )

    bind_address = settings.get(CONFIG_SECTION, "address")
    connect_address = settings.get(CONFIG_SECTION, "socket")
    db_path = settings.get(CONFIG_SECTION, "database")
    processor = InterlockProcessor(bind_address, connect_address, db_path)

    try:
        processor.listen([processor.start_task_cleaner()])
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Finish the program")
    finally:
        processor.close()
    return


if __name__ == "__main__":
    main()
