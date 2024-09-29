"""RelaxControl: watch on interlock value
and maintain target reduced voltage if it is up. 
And restore voltage level when flag is down
"""

from math import isclose
from typing import TypeAlias

import logging
import timeit

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import get_timestamp
from caen_tools.SystemCheck.utils import InterlockManager
from caen_tools.utils.receipt import ReceiptResponseError

from .metascript import Script
from .structures import InterlockState, RelaxParamsDict, Codes, CheckResult
from .receipts import PreparedReceipts, Services

Address: TypeAlias = str


class RelaxControl(Script):
    """Main class for the continious interlock control
    and voltage reducing while interlock"""

    SENDER = "syscheck/relaxcontrol"

    def __init__(
        self,
        shared_parameters: RelaxParamsDict,
        devback: Address,
        interlockdb: InterlockManager,
    ):
        logging.debug("Init RelaxControl script")
        super().__init__(shared_parameters=shared_parameters)
        self.cli = AsyncClient({Services.DEVBACK: devback})
        self.__interlockdb = interlockdb

    @property
    def target_voltage(self) -> float:
        return self.shared_parameters["target_voltage"]

    @target_voltage.setter
    def target_voltage(self, value):
        self.shared_parameters["target_voltage"] = value

    @property
    def voltage_modifier(self) -> float:
        return self.shared_parameters["voltage_modifier"]

    @voltage_modifier.setter
    def voltage_modifier(self, value):
        self.shared_parameters["voltage_modifier"] = value

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

    async def exec_function(self):
        """Logic:
        1. Get interlock state (ILS)
        2. If ILS == up -> set reduced voltage
           If ILS == down -> restore target voltage
        """

        logging.debug("Start RelaxControl script")
        starttime = timeit.default_timer()

        target_voltage: float = self.target_voltage
        voltage_modifier: float = self.voltage_modifier
        reduced_voltage: float = target_voltage * voltage_modifier
        interlock: bool = self.__interlockdb.get_interlock.current_state

        receipt = await self.cli.query(PreparedReceipts.get_voltage(self.SENDER))
        if isinstance(receipt.response, ReceiptResponseError):
            logging.error("No connection with Device during LoaderControl")
            self.form_answer(Codes.DEVBACK_ERROR)
            return
        current_voltage = receipt.response.body["multiplier"]

        if interlock and not isclose(current_voltage, reduced_voltage, abs_tol=1e-4):
            logging.info(
                "Different current (%.3f) and reduced (%.3f) voltages. Set %.3f",
                current_voltage,
                reduced_voltage,
                reduced_voltage,
            )
            await self.set_voltage(reduced_voltage)
        elif not interlock and not isclose(
            current_voltage, target_voltage, abs_tol=1e-4
        ):
            logging.info(
                "Different current (%.3f) and target (%.3f) voltages. Set %.3f",
                current_voltage,
                target_voltage,
                target_voltage,
            )
            await self.set_voltage(target_voltage)
        else:
            logging.debug("All is ok already: current voltage is %.3f", current_voltage)

        exectime = timeit.default_timer() - starttime
        logging.info("RelaxControl was done in %.3f s", exectime)
        return

    def __del__(self):
        del self.cli
        return
