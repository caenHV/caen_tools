from dataclasses import InitVar, dataclass, field
import logging
import time
from typing import ClassVar, TypeAlias, TypedDict
from enum import Enum, Flag, auto

from caen_tools.utils.utils import get_timestamp

# Alias for microservice connection_address "proto://host:port"
Address: TypeAlias = str


class Codes(Flag):
    """Enum with statuscodes"""

    OK = auto()
    DEVBACK_ERROR = auto()
    MONITOR_ERROR = auto()


class ErrorCode(Flag):
    OVERCURRENT = auto()
    SOFT_OVERCURRENT = auto()
    BADVOLTAGE = auto()
    PARAMS = auto()
    MULTIPLE = auto()
    CANT_READ = auto()

    @staticmethod
    def from_ChannelStatus(status):
        match status:
            case ChannelStatus(multiple_problems=True):
                return ErrorCode.MULTIPLE
            case ChannelStatus(bad_status=True):
                return ErrorCode.PARAMS
            case ChannelStatus(voltage_problems=True):
                return ErrorCode.BADVOLTAGE
            case ChannelStatus(current_problems=True):
                return ErrorCode.OVERCURRENT
            case ChannelStatus(soft_current_limit=True):
                return ErrorCode.SOFT_OVERCURRENT
            case _:
                logging.warning("This place must be unreachable.")
                return ErrorCode.CANT_READ


ErrorDescription: TypeAlias = str


@dataclass
class CheckStatus:
    """Statues of the performed check"""

    ack: bool
    failure: tuple[ErrorCode, ErrorDescription] | None = None


@dataclass
class InterlockState:
    """Defines a structure of given interlock state"""

    current_state: bool = None
    timestamp: int = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = get_timestamp()


@dataclass
class RampDownInfo:
    is_rdown: bool
    trip_time: float
    timestamp: float | None = None
    last_breath: bool = False

    def reset(self) -> None:
        self.is_rdown = False
        self.timestamp = None
        self.last_breath = False

    def check_trip_time(self) -> bool:
        if self.timestamp is None:
            self.timestamp = time.time()
            self.last_breath = False
            self.is_rdown = True
            return True
        is_time_exceeded = time.time() - self.timestamp < self.trip_time
        if not is_time_exceeded:
            self.reset()
            return True

        if self.last_breath:
            self.reset()
            return is_time_exceeded
        else:
            self.timestamp = time.time()
            self.last_breath = True
            self.is_rdown = False
            return True


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


class AutopilotDict(TypedDict):
    """General autopilot section structure"""

    run: list[str]


class MinimalScriptDict(TypedDict):
    """Minimal script config structure"""

    enable: bool
    repeat_every: float
    last_check: CheckResult | None


class LoaderDict(MinimalScriptDict):
    """Loader script config structure"""


class HealthParametersDict(MinimalScriptDict):
    """Defines shared parameters dict structure for HealthParameters script"""

    last_down: int | None


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


@dataclass
class ChannelStatus:
    """This dataclass represents CAEN channel statuses.

    For statuses other than 'on', 'ramp_up', and 'ramp_down': status == True means it is bad
    """

    on: bool
    ramp_up: bool
    ramp_down: bool
    over_current: bool
    over_voltage: bool
    under_voltage: bool
    max_V: bool
    max_I: bool
    trip: bool
    overpower: bool
    over_temperature: bool
    disabled: bool
    interlock: bool
    uncalibrated: bool

    is_ramping: bool = field(init=False)
    is_bad: bool = field(init=False)
    multiple_problems: bool = field(init=False)
    bad_status: bool = field(init=False)
    voltage_problems: bool = field(init=False)

    soft_current_limit: bool = field(init=False)
    current_problems: bool = field(init=False)

    current: InitVar[float]
    max_current_config: InitVar[dict[str, float | dict[str, float]]]

    ramping_mask: ClassVar[list[str]] = ["ramp_up", "ramp_down"]

    other_statuses_mask: ClassVar[list[str]] = [
        "max_V",
        "max_I",
        "trip",
        "overpower",
        "over_temperature",
        "disabled",
        "interlock",
        "uncalibrated",
    ]

    voltage_mask: ClassVar[list[str]] = ["over_voltage", "under_voltage"]
    current_mask: ClassVar[list[str]] = ["over_current"]

    def __post_init__(
        self, current: float, max_current_config: dict[str, float | dict[str, float]]
    ):
        self.is_ramping = any(
            [self.__getattribute__(stat) for stat in ChannelStatus.ramping_mask]
        )
        self.bad_status = any(
            [self.__getattribute__(stat) for stat in ChannelStatus.other_statuses_mask]
        )
        self.voltage_problems = any(
            [self.__getattribute__(stat) for stat in ChannelStatus.voltage_mask]
        )

        max_current_key = "volt_change" if self.is_ramping else "steady"
        max_current = max_current_config[max_current_key]

        self.current_problems = any(
            [self.__getattribute__(stat) for stat in ChannelStatus.current_mask]
        )
        if max_current_key == "volt_change":
            self.current_problems = self.current_problems or (current > max_current)  # type: ignore
        else:
            soft_limit, hard_limit = max_current["soft_limit"], max_current["hard_limit"]  # type: ignore
            self.soft_current_limit = current > soft_limit
            self.current_problems = self.current_problems or (current > hard_limit)

        problems = [self.bad_status, self.voltage_problems, self.current_problems]
        self.multiple_problems = len([x for x in problems if x == True]) > 1
        self.is_bad = any(problems)

    @staticmethod
    def form(
        status: str,
        current: float,
        max_current_config: dict[str, float | dict[str, float]],
    ):
        """Creates an instance of ChannelStatus

        Parameters
        ----------
        status : str
            string read out from the CAEN device. It is a decimal representation of binary status string.
            For more details read CAEN manuals (e.g. Manual for V6534 Rev9).
        current : float
            Current flowing through the channel
        max_current_config : dict[str, float | dict[str, float]]
            Configuration of the eligible currents for the given channel in the following form:
            {"volt_change" : max_current_change, "steady" : {"soft_limit" : soft_limit, "hard_limit" : hard_limit}}
            If current is over hard_limit, the current_problems is triggered.
            If soft_limit < current < hard_limit, soft_current_limit is triggered.

        Returns
        -------
        ChannelStatus
        """
        bin = [ch == "1" for ch in list(format(int(status), "015b")[::-1])]
        return ChannelStatus(
            on=bin[0],
            ramp_up=bin[1],
            ramp_down=bin[2],
            over_current=bin[3],
            over_voltage=bin[4],
            under_voltage=bin[5],
            max_V=bin[6],
            max_I=bin[7],
            trip=bin[8],
            overpower=bin[9],
            over_temperature=bin[10],
            disabled=bin[11],
            interlock=bin[12],
            uncalibrated=bin[13],
            current=current,
            max_current_config=max_current_config,
        )
