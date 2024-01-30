import configparser
import pathlib
import logging
import sys


def get_default_logger(level=logging.DEBUG):
    """Returns default logger for console printing"""

    logger = logging.getLogger(__name__)
    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s] - %(message)s"
    )
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(log_format)
    logger.addHandler(handler)
    return logger


def address_encoder(address: str) -> str:
    """Adress string encoder (useful for message routing)

    Parameters
    ----------
    address : str | None
        string name
    """

    if address is None:
        address = ""
    return address.encode("ascii")


def config_processor(configfile):
    """Opens custom config file
    (if configfile is None this uses default config)
    """

    default_config = pathlib.Path(__file__).parent.parent.parent / "config.ini"
    configs = [default_config]

    settings = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation()
    )
    if configfile is not None:
        configs.append(configfile.name)

    settings.read(configs)
    return settings
