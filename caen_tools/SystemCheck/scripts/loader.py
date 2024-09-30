"""Loader Control: gets data from device backend 
and sends it to Monitor (for ODB writing)"""

from typing import TypeAlias
import timeit
import logging

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.receipt import ReceiptResponseError
from .structures import LoaderDict, Codes, CheckResult
from .metascript import Script
from .receipts import Services, PreparedReceipts

Address: TypeAlias = str


class LoaderControl(Script):
    """Logic:
    1. asks devback for parameters (self.__parameters)
    2. sends parameters to monitor service
    """

    SENDER = "syscheck/loader"

    def __init__(
        self, shared_parameters: LoaderDict, device_backend: Address, monitor: Address
    ):
        super().__init__(shared_parameters=shared_parameters)
        self.__cli = AsyncClient(
            {
                Services.DEVBACK: device_backend,
                Services.MONITOR: monitor,
            }
        )
        self.__parameters = ["VMon", "IMonH", "IMonL", "ChStatus", "ImonRange"]

    def form_answer(self, code: Codes):
        self.shared_parameters["last_check"] = CheckResult(code)

    def get_time(self, starttime):
        """Utility method to get time difference"""
        return timeit.default_timer() - starttime

    async def exec_function(self):

        starttime = timeit.default_timer()
        # 1. Get parameters from DEVBACK
        devpars = await self.__cli.query(
            PreparedReceipts.get_params(self.SENDER, self.__parameters)
        )
        if isinstance(devpars.response, ReceiptResponseError):
            logging.error("No connection with DevBackend during LoaderControl")
            self.form_answer(Codes.DEVBACK_ERROR)
            return
        logging.debug(
            "LoaderControl: got devback params in %.3f", self.get_time(starttime)
        )

        # 2. Put parameters into MON
        moncheck = await self.__cli.query(
            PreparedReceipts.put2mon(self.SENDER, devpars.response.body["params"])
        )
        if isinstance(moncheck.response, ReceiptResponseError):
            logging.error("No connection with Monitor during LoaderControl")
            self.form_answer(Codes.MONITOR_ERROR)
            return
        logging.debug("LoaderControl: send to mon in %.3f", self.get_time(starttime))

        # 3. Finish
        self.form_answer(Codes.OK)
        exectime = timeit.default_timer() - starttime
        logging.info("LoaderControl was done in %.3f s", exectime)
        return
