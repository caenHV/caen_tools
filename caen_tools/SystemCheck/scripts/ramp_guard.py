"""ReducerControl: decreases and restores 
the voltage at time intervals
"""

from typing import TypeAlias

import asyncio
import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError
from .metascript import Script
from .structures import RampGuardParametersDict, Codes, CheckResult
from .receipts import Services, PreparedReceipts
from .mchswork import MChSWorker

Address: TypeAlias = str


class RampGuard(Script):
    """Main script for controlling ramp up/down state"""

    SENDER = "syscheck/rampguard"
    MCHS_KEY = "noramping"

    def __init__(
        self,
        shared_parameters: RampGuardParametersDict,
        device: Address,
        mchs: MChSWorker,
    ):
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient({Services.DEVBACK: device})
        self.mchs = mchs

    def form_answer(self, code: Codes) -> None:
        self.shared_parameters["last_check"] = CheckResult(code)
        return

    async def is_ramping(self):
        """Sends a receipt to devicebackend to get parameters (status) and checks that channels are not in ramp up/down state."""
        receipt = await self.cli.query(
            PreparedReceipts.get_params(self.SENDER, ["ChStatus"])
        )
        if isinstance(receipt.response, ReceiptResponseError):
            logging.error("No connection with Device during RampGuard.get_status")
            self.form_answer(Codes.DEVBACK_ERROR)
            return
        self.form_answer(Codes.OK)

        params: dict = receipt.response.body["params"]

        def is_ramping_status(ch_status: str) -> bool:
            st = format(int(ch_status), "015b")[::-1]
            return st[1] == "1" or st[2] == "1"

        is_ramping = False
        try:
            is_ramping = any(
                [is_ramping_status(val["ChStatus"]) for val in params.values()]
            )
        except KeyError as e:
            logging.warning("RampGuard could not access ChStatus: %s", e)
        return is_ramping

    def send_mchs(self, status: bool) -> None:
        """Sends ACK (True) or NACK (False) on MChS"""
        self.mchs.set_state(**{self.MCHS_KEY: status})
        self.mchs.send_state()
        return

    # ----------------------

    async def exec_function(self):
        """Logic:
        Get channels statuses
        If any any channel has Ramp up or Ramp down but up ->
            send NACK to MCHS
        else ->
            script done
        """

        logging.debug("Start RampGuard script")
        starttime = timeit.default_timer()

        is_ramping = await self.is_ramping()
        self.send_mchs(not is_ramping)

        exectime = timeit.default_timer() - starttime
        logging.info("ReducerControl was done in %.3f s", exectime)

    async def on_stop(self):
        self.mchs.pop_keystate(self.MCHS_KEY)

    def __del__(self):
        del self.cli
        return
