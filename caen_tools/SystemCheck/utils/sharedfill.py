"""A number of utilty functions"""

import logging
import multiprocessing as mp

from caen_tools.SystemCheck.scripts.structures import (
    MCHSDict,
    LoaderDict,
    InterlockParametersDict,
    HealthParametersDict,
    RelaxParamsDict,
    ReducerParametersDict,
    RampGuardParametersDict,
    SharedParametersDict,
)


def sharedmemo_fillup(
    manager: mp.Manager, settings: dict, section: str
) -> SharedParametersDict:
    """Fill up shared memory from config file"""

    mchs_section = f"{section}.mchs"
    mchs: MCHSDict = dict(
        udp_ip=settings.get(mchs_section, "host"),
        udp_port=settings.get(mchs_section, "port"),
        client_id=settings.get(mchs_section, "client_id"),
    )
    logging.debug("MChS defaults: %s", mchs)

    loader_section = f"{section}.loader"
    loader: LoaderDict = manager.dict(
        enable=settings.getboolean(loader_section, "enable"),
        repeat_every=settings.getfloat(loader_section, "repeat_every"),
        last_check=None,
    )
    logging.debug("Loader defaults: %s", loader)

    health_section = f"{section}.health"
    health: HealthParametersDict = manager.dict(
        enable=settings.getboolean(health_section, "enable"),
        repeat_every=settings.getfloat(health_section, "repeat_every"),
        last_check=None,
    )
    logging.debug("Health defaults: %s", health)

    interlock_section = f"{section}.interlock"
    interlock: InterlockParametersDict = manager.dict(
        enable=settings.getboolean(interlock_section, "enable"),
        repeat_every=settings.getfloat(interlock_section, "repeat_every"),
        last_check=None,
    )
    logging.debug("Interlock defaults: %s", interlock)

    relax_section = f"{section}.autopilot.relax"
    relax: RelaxParamsDict = manager.dict(
        enable=settings.getboolean(relax_section, "enable"),
        repeat_every=settings.getfloat(relax_section, "repeat_every"),
        last_check=None,
        voltage_modifier=settings.getfloat(relax_section, "voltage_modifier"),
        target_voltage=settings.getfloat(relax_section, "target_voltage"),
    )
    logging.debug("Relax defaults: %s", relax)

    reducer_section = f"{section}.autopilot.reducer"
    reducer: ReducerParametersDict = manager.dict(
        enable=settings.getboolean(reducer_section, "enable"),
        repeat_every=settings.getfloat(reducer_section, "repeat_every"),
        last_check=None,
        voltage_modifier=settings.getfloat(reducer_section, "voltage_modifier"),
        target_voltage=settings.getfloat(reducer_section, "target_voltage"),
        reducing_period=settings.getfloat(reducer_section, "reducing_period"),
    )
    logging.debug("Reducer defaults: %s", reducer)

    ramp_guard_section = f"{section}.autopilot.ramp_guard"
    ramp_guard: RampGuardParametersDict = manager.dict(
        enable=settings.getboolean(reducer_section, "enable"),
        repeat_every=settings.getfloat(reducer_section, "repeat_every"),
        last_check=None,
    )
    logging.debug("RampGuard defaults: %s", ramp_guard)

    shared_parameters = manager.dict(
        loader=loader,
        health=health,
        interlock=interlock,
        relax=relax,
        reducer=reducer,
        ramp_guard=ramp_guard,
        mchs=mchs,
    )

    return shared_parameters
