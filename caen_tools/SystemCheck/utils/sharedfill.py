"""A number of utilty functions"""

import logging
import multiprocessing as mp

from .structures import (
    AutopilotDict,
    MCHSDict,
    LoaderDict,
    InterlockParametersDict,
    HealthParametersDict,
    RelaxParamsDict,
    ReducerParametersDict,
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
        low_voltage_mlt=settings.getfloat(health_section, "low_voltage_mlt"),
        soft_reduce_mod=settings.getfloat(health_section, "soft_reduce_modifier"),
        auto_restart=settings.getboolean(health_section, "auto_restart_autopilot"),
        auto_restart_after=settings.getfloat(health_section, "auto_restart_after"),
        allowed_down_window=settings.getfloat(health_section, "allowed_down_window"),
        n_allowed_downs=settings.getint(health_section, "n_consecutive_downs"),
        reduce_period=settings.getfloat(health_section, "reduce_period"),
        last_down=None,
        reduced=None,
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

    autopilot_section = f"{section}.autopilot"
    autopilot: AutopilotDict = manager.dict(
        run=list(
            filter(
                lambda x: x != "",
                map(
                    lambda x: x.strip(),
                    settings.get(autopilot_section, "run").split(","),
                ),
            ),
        ),
    )
    logging.debug("Autopilot defaults: %s", autopilot)

    relax_section = f"{section}.autopilot.relax"
    relax: RelaxParamsDict = manager.dict(
        enable=False,
        repeat_every=settings.getfloat(relax_section, "repeat_every"),
        last_check=None,
        voltage_modifier=settings.getfloat(relax_section, "voltage_modifier"),
        target_voltage=settings.getfloat(relax_section, "target_voltage"),
    )
    logging.debug("Relax defaults: %s", relax)

    reducer_section = f"{section}.autopilot.reducer"
    reducer: ReducerParametersDict = manager.dict(
        enable=False,
        repeat_every=settings.getfloat(reducer_section, "repeat_every"),
        last_check=None,
        voltage_modifier=settings.getfloat(reducer_section, "voltage_modifier"),
        target_voltage=settings.getfloat(reducer_section, "target_voltage"),
        reducing_period=settings.getfloat(reducer_section, "reducing_period"),
    )
    logging.debug("Reducer defaults: %s", reducer)

    shared_parameters = manager.dict(
        loader=loader,
        health=health,
        interlock=interlock,
        autopilot=autopilot,
        relax=relax,
        reducer=reducer,
        mchs=mchs,
    )

    return shared_parameters
