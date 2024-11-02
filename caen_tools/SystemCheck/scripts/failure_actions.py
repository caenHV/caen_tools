import logging
import time
from caen_tools.SystemCheck.scripts.health import HealthControl
from caen_tools.SystemCheck.scripts.receipts.listreceipts import PreparedReceipts
from caen_tools.SystemCheck.utils.structures import CheckStatus
from caen_tools.utils.receipt import ReceiptResponseError


async def failure_actions(hc: HealthControl, status: CheckStatus) -> None:
    """A number of actions on failure"""

    logging.error("Bad device parameters. Emergency DownVoltage!", stack_info=True)

    for script in hc.dependent_scripts:
        script.stop()

    # Send bad news on mchs
    hc.send_mchs(False)

    logging.debug("Send Down Voltage Receipt", stack_info=True)
    down_voltage = await hc.cli.query(PreparedReceipts.down(hc.SENDER))
    logging.info(
        "Send emergency status of the device: is_ok = %s, description = %s",
        False,
        status.failure[1],  # type: ignore
        stack_info=True,
    )

    if isinstance(down_voltage.response, ReceiptResponseError):
        logging.error(
            "Not sent DownVoltage Receipt (%s)! Try again...",
            down_voltage.response,
            stack_info=True,
        )
        down_voltage = await hc.cli.query(PreparedReceipts.down(hc.SENDER))
        logging.info("Final response (%s)", down_voltage.response, stack_info=True)

    await hc.cli.query(PreparedReceipts.reset_device(hc.SENDER))

    hc.shared_parameters["last_down"] = time.time()
    hc._num_downs.increment(1)
    await hc.cli.query(
        PreparedReceipts.sendlog(
            hc.SENDER,
            (
                f"{status.failure[0]}: {status.failure[1]}"
                if status is not None
                else "Down voltage due to bad device params (generic error)"
            ),
            True,
        ),
        receive_time=0.5,
    )

    return


async def get_target_voltage(
    hc: HealthControl,
) -> float | None:
    autopilot_status = await hc.cli.query(
        PreparedReceipts.get_autopilot_params(hc.SENDER), 1
    )
    response = autopilot_status.response
    if isinstance(response, ReceiptResponseError):
        logging.warning("Problem with autopilot status %s", response)
        return None
    return response.body["autopilot"].get("target_voltage", None)  # type: ignore


async def reduce_voltage(hc: HealthControl, status: CheckStatus) -> None:
    """A number of actions on failure"""

    logging.error(
        "Electrical breakdown is detected. Reducing voltage!", stack_info=True
    )

    for script in hc.dependent_scripts:
        script.stop()

    # Send bad news on mchs (read more about it here https://t.ly/_Ibe8)
    hc.send_mchs(False)
    target = await get_target_voltage(hc)
    if target is None:
        logging.debug(
            "The voltage target is None. Send Down Voltage Receipt", stack_info=True
        )
        await hc.cli.query(PreparedReceipts.down(hc.SENDER))
        return

    logging.debug("Send Reduce Voltage Receipt", stack_info=True)
    reduce_voltage = await hc.cli.query(
        PreparedReceipts.set_voltage(hc.SENDER, target * hc._soft_reduce_mod)
    )
    if isinstance(reduce_voltage.response, ReceiptResponseError):
        logging.warning(
            "Problem with reducing voltage %s. Sending DownVoltage.",
            reduce_voltage.response,
            stack_info=True,
        )
        await hc.cli.query(PreparedReceipts.down(hc.SENDER))
        return None

    logging.info(
        "Send electrical breakdown status of the device: is_ok = %s, description = %s",
        False,
        status.failure[1],
        stack_info=True,
    )

    hc.shared_parameters["reduced"] = time.time()
    hc._num_breakdowns.increment(1)
    await hc.cli.query(
        PreparedReceipts.sendlog(
            hc.SENDER,
            (
                f"{status.failure[0]}: {status.failure[1]}"
                if status is not None
                else "electrical breakdown due to soft over current (generic)"
            ),
            True,
        ),
        receive_time=0.5,
    )

    return


async def setup_autopilot(hc: HealthControl) -> bool:
    target_voltage = await get_target_voltage(hc)
    if target_voltage is not None:
        autopilot_restart = await hc.cli.query(
            PreparedReceipts.set_autopilot(hc.SENDER, True, target_voltage), 1
        )
        if isinstance(autopilot_restart.response, ReceiptResponseError):
            logging.warning(
                "Problem with autopilot start %s",
                autopilot_restart.response,
                stack_info=True,
            )
            return False
        logging.info(
            "Autopilot was restarted after emergency down with target voltage = %s",
            target_voltage,
            stack_info=True,
        )
        return True
    return False


async def check_and_increase(hc: HealthControl):
    """Checks that is the number of consecutive electrical breakdowns down is small and enough time from last breakdown elapsed.
    If it is the case, the function is doing the following:
        1) Set autopilot with the previous target.
        2) reduced = None
    If too many electrical breakdowns occurred in the breakdown_time_window:
        1) reduced = None
        2) last_down = now
        3) Sends DownVoltage

    Parameters
    ----------
    hc : HealthControl
    """
    if hc.shared_parameters["reduced"] is None:
        return

    n_breakdowns = hc._num_breakdowns.count
    if n_breakdowns > hc._n_allowed_downs:
        hc.shared_parameters["reduced"] = None
        if hc.shared_parameters["auto_restart"]:
            hc.shared_parameters["last_down"] = time.time()
        logging.warning(
            "Too many electrical breakdowns (%s) in last %s seconds. Send DownVoltage.",
            n_breakdowns,
            hc._breakdown_time_window,
        )
        await hc.cli.query(PreparedReceipts.down(hc.SENDER))
        return
    if time.time() - hc.shared_parameters["reduced"] > hc._reduce_period:
        hc.shared_parameters["reduced"] = None
        await setup_autopilot(hc)


async def check_and_restart(hc: HealthControl):
    """Checks that is the number of consecutive break down is small and enough time from last down elapsed.
    If it is the case, the function is doing the following:
        1) Reset channels
        2) last_down = None
        3) Sets autopilot with the previous target.

    Parameters
    ----------
    hc : HealthControl
    """
    if hc.shared_parameters["last_down"] is None:
        return

    n_consecutive_downs = hc._num_downs.count

    if n_consecutive_downs > hc._n_allowed_downs:
        hc.shared_parameters["last_down"] = None
        hc.shared_parameters["reduced"] = None
        hc.shared_parameters["auto_restart"] = False
        logging.warning(
            "Too many emergency downs (%s) in last %s seconds. Autopilot will not be restarted.",
            n_consecutive_downs,
            hc._allowed_down_window,
        )
        return

    logging.debug(
        "Last down timestamp is = %s, autorestart time = %s",
        hc.shared_parameters["last_down"],
        hc._auto_restart_after,
    )
    if time.time() - hc.shared_parameters["last_down"] > hc._auto_restart_after:
        await hc.cli.query(PreparedReceipts.reset_device(hc.SENDER))
        hc.shared_parameters["last_down"] = None
        await setup_autopilot(hc)
