from dataclasses import dataclass
from typing import TypedDict
from enum import Flag, auto

from caen_tools.utils.utils import get_timestamp


class Codes(Flag):
    """Enum with statuscodes"""

    OK = auto()
    DEVBACK_ERROR = auto()
    MONITOR_ERROR = auto()


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


@dataclass
class CheckResult:
    """Configuration of the check result"""

    statuscode: Codes
    timestamp: int = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = get_timestamp()


class MinimalScriptDict(TypedDict):
    """Minimal script config structure"""

    enable: bool
    repeat_every: float
    last_check: CheckResult | None


class LoaderDict(MinimalScriptDict):
    """Loader script config structure"""


class HealthParametersDict(MinimalScriptDict):
    """Defines shared parameters dict structure for HealthParameters script"""


class InterlockParametersDict(MinimalScriptDict):
    """Defines shared parameters dict structure for Interlock polling script"""


class RelaxParamsDict(MinimalScriptDict):
    """Defines shared parameters dict structure for RelaxControl script"""

    voltage_modifier: float
    target_voltage: float


class ReducerParametersDict(RelaxParamsDict):
    """Defines shared parameters dict structure for ScheduledReducer script"""

    reducing_time: float


class SharedParametersDict(TypedDict):
    """Shared memory dictionary"""

    loader: LoaderDict
    health: HealthParametersDict
    interlock: InterlockParametersDict
    relax: RelaxParamsDict
    reducer: ReducerParametersDict
    mchs: MCHSDict
