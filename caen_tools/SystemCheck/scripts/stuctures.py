from dataclasses import dataclass
from typing import TypedDict

from caen_tools.utils.utils import get_timestamp


@dataclass
class InterlockState:
    """Defines a structure of given interlock state"""

    current_state: bool = None
    timestamp: int = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = get_timestamp()


class MCHSDict(TypedDict):
    """MChS config structure"""

    udp_ip: str
    udp_port: str
    client_id: str


class InterlockParamsDict(TypedDict):
    """Defines shared parameters dict structure for InterlockControl script"""

    enable: bool
    repeat_every: int
    voltage_modifier: float
    last_check: int


class HealthParametersDict(TypedDict):
    """Defines shared parameters dict structure for HealthParameters scenario"""

    enable: bool
    repeat_every: int
    last_check: int
