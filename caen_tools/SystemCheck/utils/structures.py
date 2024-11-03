from configparser import ConfigParser
from dataclasses import InitVar, dataclass, field
import json
import logging
import time
from typing import ClassVar, TypeAlias, TypedDict
from enum import Flag, auto

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
class HealthControlSettings:
    shared_parameters: HealthParametersDict
    devback: Address
    monitor: Address
    check: Address
    low_voltage_mlt: float
    max_currents: dict[str, dict[str, float | dict[str, float]]]
    ramp_down_trip_time: dict[str, RampDownInfo]
    allowed_down_window: float
    breakdown_time_window: float
    n_allowed_downs: int
    auto_restart_after: float
    reduce_period: float
    soft_reduce_mod: float

    def __init__(self, settings: ConfigParser, section: str, shared_parameters):
        self.shared_parameters = shared_parameters
        self.devback = settings.get(section, "device_backend", fallback="")
        self.monitor = settings.get(section, "monitor", fallback="")
        self.check = settings.get(section, "system_check", fallback="")
        # self.mchs to be added lately
        self.low_voltage_mlt = settings.getfloat(section, "low_voltage_mlt", fallback=1)
        if self.low_voltage_mlt < 0 or self.low_voltage_mlt > 1.2:
            raise ValueError(
                f"low_voltage_mlt parameter in section {section} must be between non-negative and smaller than 1.2"
            )

        self.max_currents = self.__parse_max_currents(
            settings.get(f"{section}.health", "health_check_config_path")
        )
        self.ramp_down_trip_time = self.__parse_trip_time(
            settings.get(f"{section}.health", "health_check_config_path")
        )
        self.allowed_down_window = settings.getfloat(
            section, "allowed_down_window", fallback=0
        )
        self.breakdown_time_window = settings.getfloat(
            section, "breakdown_time_window", fallback=0
        )
        self.n_allowed_downs = settings.getint(
            section, "n_consecutive_downs", fallback=0
        )
        self.auto_restart_after = settings.getfloat(
            section, "auto_restart_autopilot", fallback=0
        )
        self.reduce_period = settings.getfloat(section, "reduce_period", fallback=0)
        self.soft_reduce_mod = settings.getfloat(
            section, "soft_reduce_modifier", fallback=0
        )
        if self.soft_reduce_mod > 1 or self.soft_reduce_mod < 0:
            raise ValueError(
                f"soft_reduce_mod parameter in section {section} must be between 0 and 1."
            )

    @staticmethod
    def __parse_max_currents(health_config_path: str) -> dict:
        """Opens health_check config and parses it to retrieve max currents map"""
        max_currents_map = None
        try:
            with open(health_config_path, "r", encoding="utf-8") as f:
                max_currents_map = json.load(f)["max_current"]
        except json.JSONDecodeError as e:
            logging.warning("Invalid JSON syntax in health_config_path: %s", e)
            raise e
        except OSError as e:
            logging.warning("health_config_path points to a nonexistent file: %s", e)
            raise e

        return max_currents_map

    @staticmethod
    def __fill_ramp_down_info(trip_time_map: dict) -> dict[str, RampDownInfo]:
        try:
            rdown_info = {
                ch: RampDownInfo(is_rdown=False, trip_time=float(trip_time))
                for ch, trip_time in trip_time_map.items()
            }
        except ValueError as e:
            logging.warning(
                "Ramp down trip times in health_config have to be float values: %s", e
            )
            raise e
        return rdown_info

    @staticmethod
    def __parse_trip_time(health_config_path: str) -> dict[str, RampDownInfo]:
        """Opens health_check config and parses it to retrieve ramp down trip time map"""
        try:
            with open(health_config_path, "r", encoding="utf-8") as f:
                ramp_down_trip_time = json.load(f)["ramp_down_trip_time"]

            ramp_down_trip_time = HealthControlSettings.__fill_ramp_down_info(
                ramp_down_trip_time
            )
        except json.JSONDecodeError as e:
            logging.warning("Invalid JSON syntax in health_config_path: %s", e)
            raise e
        except OSError as e:
            logging.warning("health_config_path points to a nonexistent file: %s", e)
            raise e

        return ramp_down_trip_time


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
        self.soft_current_limit = False
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
