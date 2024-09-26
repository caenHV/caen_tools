"""Small utility helpful functions"""

from pathlib import Path

import configparser
import time
import logging
from logging.config import dictConfig
from datetime import datetime
from pytz import timezone


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
    filepath: Path | None = None,
    console_output: bool = True,
    level=logging.INFO,
    backup_count: int = 15,
) -> None:
    """Configure logging.

    Parameters
    ----------
    filepath : Path | None, optional
        Path to the actual file, by default None
        On rotating it also sets the filename suffix. Rotating happens every midnight.
    console_output : bool, optional
        Mirror logging info to the stream, by default True
    level : _type_, optional
        _description_, by default logging.INFO
    backup_count : int, optional
        If backupCount is nonzero, at most backupCount files will be kept,
        and if more would be created when rollover occurs,
        the oldest one is deleted. By default backup_count = 15.
    """
    handlers = []
    if console_output:
        handlers.append("stream")
    if (filepath is not None) and not (filepath == ""):
        handlers.append("default")
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    # Sets timezone of timestamps in the log file to Novosibirsk Time.
    tz = timezone("Asia/Novosibirsk")
    logging.Formatter.converter = lambda *args: datetime.now(tz).timetuple()
    LOGGING_CONFIG = {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(filename)s line %(lineno)d: %(message)s",
                "datefmt": "%Y-%m-$d %H:%M:%S UTC+7",
            }
        },
        "handlers": {
            "default": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "default",
                "filename": filepath,
                "when": "midnight",
                "encoding": "utf-8",
                "backupCount": backup_count,
            },
            "stream": {
                "class": "logging.handlers.StreamHandler",
                "formatter": "default",
            },
        },
        "root": {"level": level, "handlers": handlers},
    }
    dictConfig(LOGGING_CONFIG)
    logging.debug("Set logging settings")
    return
