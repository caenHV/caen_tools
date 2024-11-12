from dataclasses import dataclass
from enum import IntEnum
from time import time
from typing import TypeAlias

Address: TypeAlias = str


class EventCode(IntEnum):
    """List of event codes"""

    START = 0
    STOP = 1


class Mode(IntEnum):
    """Enum of reading modes"""

    MANUAL = 0  # manual local set/get mode
    SOCKET = 1  # get interlock from socket (set is not available)


@dataclass
class InterlockResponse:
    """Interlock response format"""

    value: bool
    timestamp: int = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(time())
