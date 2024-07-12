"""Small utility helpful functions"""

from pathlib import Path

import configparser
import time
import logging


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
        allow_no_value=True,
    )
    if configfile is not None:
        configs.append(configfile.name)

    settings.read(configs)
    return settings


def get_timestamp() -> int:
    """Returns current timestamp (in seconds)"""
    return int(time.time())


def get_logging_config(
    filepath: Path | None = None, console_output: bool = True, level=logging.INFO
) -> None:
    """Sets logging.baseConfig"""
    handlers = []
    if console_output:
        handlers.append(logging.StreamHandler())
    if (filepath is not None) and not (filepath == ""):
        handlers.append(logging.FileHandler(filepath))
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    logging.basicConfig(
        handlers=handlers,
        level=level,
        encoding="utf-8",
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )
    logging.debug("Set logging settings")
    return
