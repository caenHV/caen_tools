from dataclasses import dataclass
from pathlib import Path
import json
import logging


def parse_max_currents(health_config_path: Path) -> dict:
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


def fill_ramp_down_info(trip_time_map: dict) -> dict[str, RampDownInfo] | None:
    rdown_info = None
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


def parse_trip_time(health_config_path: Path) -> dict[str, RampDownInfo] | None:
    """Opens health_check config and parses it to retrieve ramp down trip time map"""

    ramp_down_trip_time = None
    try:
        with open(health_config_path, "r", encoding="utf-8") as f:
            ramp_down_trip_time = json.load(f)["ramp_down_trip_time"]

        ramp_down_trip_time = fill_ramp_down_info(ramp_down_trip_time)
    except json.JSONDecodeError as e:
        logging.warning("Invalid JSON syntax in health_config_path: %s", e)
        raise e
    except OSError as e:
        logging.warning("health_config_path points to a nonexistent file: %s", e)
        raise e

    return ramp_down_trip_time
