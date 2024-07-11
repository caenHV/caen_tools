import configparser
from pathlib import Path
import time


def root_project() -> Path:
    """Returns root directory of this project"""

    return Path(__file__).parent.parent


def config_processor(configfile):
    """Opens custom config file
    (if configfile is None this uses default config)
    """

    default_config = root_project() / "configs" / "config.ini"
    configs = [default_config]

    settings = configparser.ConfigParser(
        defaults={"root_configs": root_project() / "configs"},
        interpolation=configparser.ExtendedInterpolation(),
    )
    if configfile is not None:
        configs.append(configfile.name)

    settings.read(configs)
    return settings


def get_timestamp() -> int:
    """Returns current timestamp (in seconds)"""
    return int(time.time())
