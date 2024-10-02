"""ReducerControl: decreases and restores 
the voltage at time intervals
"""

from typing import TypeAlias

import asyncio
import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.SystemCheck.utils import InterlockManager
from caen_tools.utils.receipt import ReceiptResponseError
from .metascript import Script
from .structures import ReducerParametersDict, Codes, CheckResult
from .receipts import Services, PreparedReceipts
from .mchswork import MChSWorker
from .relax import RelaxControl

Address: TypeAlias = str


class ReducerControl(Script):
    """Main script for reducing voltage at time intervals"""

    SENDER = "syscheck/reducercontrol"
    MCHS_KEY = "noreducing"

    def __init__(
        self,
        shared_parameters: ReducerParametersDict,
        device: Address,
        interlockdb: InterlockManager,
        mchs: MChSWorker,
        relax: RelaxControl,
    ):
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient({Services.DEVBACK: device})
        self.interlockdb = interlockdb
        self.mchs = mchs
        self.relax = relax

    async def interlock_status(self) -> bool:
        state = await self.interlockdb.get_interlock()
        return state.current_state

    @property
    def target_voltage(self) -> float:
        return self.shared_parameters["target_voltage"]

    @property
    def reduced_voltage(self) -> float:
        return self.target_voltage * self.shared_parameters["voltage_modifier"]

    def form_answer(self, code: Codes) -> None:
        self.shared_parameters["last_check"] = CheckResult(code)
        return

    async def set_voltage(self, target_level: float):
        """Sends a receipt to devicebackend to set voltage"""
        receipt = await self.cli.query(
            PreparedReceipts.set_voltage(self.SENDER, target_level)
        )
        if isinstance(receipt.response, ReceiptResponseError):
            logging.error("No connection with Device during RelaxControl.set_voltage")
            self.form_answer(Codes.DEVBACK_ERROR)
            return

        self.form_answer(Codes.OK)
        return

    def send_mchs(self, status: bool) -> None:
        """Sends ACK (True) or NACK (False) on MChS"""
        self.mchs.set_state(**{self.MCHS_KEY: status})
        self.mchs.send_state()
        return

    # ----------------------

    async def exec_function(self):
        """Logic:
        Check interlock (ILK)
        If ILK True ->
          script done
        else ->
          reduce voltage
          wait during time_period
          check interlock
          If ILK True ->
            script done
          else ->
            restore voltage
            script done
        """
        logging.debug("Start ReducerControl script")

        # Start logic in the end of the cycle time interval
        waiting_time = max(
            0,
            self.shared_parameters["repeat_every"]
            - self.shared_parameters["reducing_period"],
        )
        logging.debug("Wait for %s", waiting_time)
        await asyncio.sleep(waiting_time)

        starttime = timeit.default_timer()

        if await self.interlock_status():
            self.form_answer(Codes.OK)
            return

        logging.debug("ReducerControl: it's time to reduce voltage")
        self.send_mchs(False)
        relax_params = (self.relax.target_voltage, self.relax.voltage_modifier)
        self.relax.target_voltage, self.relax.voltage_modifier = self.reduced_voltage, 1
        logging.debug(
            "ReducerControl: %s %s",
            self.relax.target_voltage,
            self.relax.voltage_modifier,
        )
        await self.set_voltage(self.reduced_voltage)

        # Waiting time
        logging.debug("ReducerControl: chill out")
        reduced_period = self.shared_parameters["reducing_period"]
        await asyncio.sleep(reduced_period)

        self.relax.target_voltage, self.relax.voltage_modifier = (
            relax_params[0],
            relax_params[1],
        )
        logging.error(
            "VALS %s %s", self.relax.target_voltage, self.relax.voltage_modifier
        )
        if await self.interlock_status():
            logging.debug(
                "ReducerControl: Interlock is up. No needs to restore voltage"
            )
            self.form_answer(Codes.OK)
            self.send_mchs(True)
        else:
            logging.debug("ReducerControl: restore voltage")
            await self.set_voltage(self.target_voltage)
            await asyncio.sleep(30)  # waiting for when voltage will raise
            self.send_mchs(True)

        exectime = timeit.default_timer() - starttime
        logging.info("ReducerControl was done in %.3f s", exectime)

    async def on_stop(self):
        self.mchs.pop_keystate(self.MCHS_KEY)

    def __del__(self):
        del self.cli
        return
