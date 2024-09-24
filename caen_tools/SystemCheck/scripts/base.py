"""A set of different system check scenarios"""

import timeit
import logging

from caen_tools.connection.client import AsyncClient
from caen_tools.SystemCheck.utils import check_process
from caen_tools.SystemCheck.utils import send_udp_to_mchs_controller
from caen_tools.utils.receipt import Receipt
from caen_tools.utils.utils import get_timestamp

SRV_NAME = "syscheck"

DOWN_RPT = Receipt(
    sender=SRV_NAME,
    executor="devback",
    title="down",
    params={},
)

USRVLT_RPT = Receipt(
    sender=SRV_NAME,
    executor="devback",
    title="last_user_voltage",
    params={},
)


def set_voltage_receipt(target_voltage: float) -> Receipt:
    """Partial for set voltage receipt"""
    return Receipt(
        sender=SRV_NAME,
        executor="devback",
        title="set_voltage",
        params={"target_voltage": target_voltage},
    )



@check_process(1)
async def base_scenario(cli: AsyncClient, shared_parameters: dict):
    """Main system check scenario

    Parameters
    ----------
    cil : AsyncClient
        client to connect with microservices friends
    shared_parameters : dict
        shared memory dictionary keeping metadata
        (use carefully)
    """

    starttime = timeit.default_timer()

    # Read current state of CAEN
    devpars_receipt = Receipt(
        sender=SRV_NAME,
        executor="devback",
        title="params",
        params={},
    )
    devpars = await cli.query(devpars_receipt)
    logging.debug("Devpars %s", devpars)

    # Put these parameters into monitor
    put_receipt = Receipt(
        sender=SRV_NAME,
        executor="monitor",
        title="send_params",
        params={"params": devpars.response.body["params"]},
    )
    # Monitor provides status of uploaded data (ok or not ok)
    moncheck = await cli.query(put_receipt)

    # Default behaviour: to Down voltage if parameters are bad
    paramsok = moncheck.response.body["params_ok"]

    if not paramsok:
        logging.error("Bad deivce parameters. Emergency DownVoltage!")
        send_udp_to_mchs_controller(
            udp_ip=shared_parameters["mchs"]["host"],
            udp_port=shared_parameters["mchs"]["port"],
            client_id=shared_parameters["mchs"]["id"],
            ack=False,
        )
        await cli.query(DOWN_RPT)
        return

    # Interlock logic
    # If follow interlock do something else

    if shared_parameters.get("interlock").get("follow") is True:
        interlock = moncheck.response.body["interlock"]
        last_interlock_state = shared_parameters["interlock"]["last_interlock_state"]

        if last_interlock_state is None:
            last_interlock_state = interlock

        if interlock and not last_interlock_state:
            trgresp = await cli.query(USRVLT_RPT)
            user_voltage = trgresp.response.body["last_user_voltage"]
            voltage_mlt = shared_parameters.get("interlock").get("voltage_modifier")
            target_voltage = user_voltage * voltage_mlt
            logging.info("Interlock has been set. Set voltage %s", target_voltage)
            await cli.query(set_voltage_receipt(target_voltage))

        if not interlock and last_interlock_state:
            trgresp = await cli.query(USRVLT_RPT)
            target_voltage = trgresp.response.body["last_user_voltage"]
            logging.info("Interlock turned off. Set voltage %s", target_voltage)
            await cli.query(set_voltage_receipt(target_voltage))

        shared_parameters["interlock"]["last_interlock_state"] = interlock

    send_udp_to_mchs_controller(
        udp_ip=shared_parameters["mchs"]["host"],
        udp_port=shared_parameters["mchs"]["port"],
        client_id=shared_parameters["mchs"]["id"],
        ack=True,
    )

    exectime = timeit.default_timer() - starttime
    logging.info("Base check is completed in %.3f s", exectime)

    # If all is ok write the time
    # of the last check in the shared memory
    # for SysCheck status API
    shared_parameters["last_check"] = get_timestamp()

    return


# Extra checking scenarios can be added
# like in the following code
# To run them mention it also in worker.py
#
# @check_process(5)
# async def extra_scenario():
#     await asyncio.sleep(1)
#     logging.info("Check %s is completed", t)
