from pathlib import Path
import json
import logging


def parse_max_currents(max_currents_map_path: Path) -> dict:
    """Opens max current map config and parses it"""

    max_currents_map = None
    try:
        with open(max_currents_map_path, "r", encoding="utf-8") as f:
            max_currents_map = json.load(f)["max_current"]
    except json.JSONDecodeError as e:
        logging.warning("Invalid JSON syntax in max_currents_map_path: %s", e)
        raise e
    except OSError as e:
        logging.warning("max_currents_map_path points to a nonexistent file: %s", e)
        raise e

    return max_currents_map
