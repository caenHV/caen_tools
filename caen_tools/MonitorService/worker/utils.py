from enum import Flag, auto
from typing import TypeAlias


Address: TypeAlias = str


class Services:
    """List of services"""

    MONITOR = "monitor"
    DEVBACK = "devback"
    CHECK = "syscheck"


class Codes(Flag):
    """Enum with statuscodes"""

    OK = auto()
    DEVBACK_ERROR = auto()
    MONITOR_ERROR = auto()
