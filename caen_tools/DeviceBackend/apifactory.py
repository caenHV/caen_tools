"""Defines API methods for DeviceBackend microservice"""

import json
import logging
from caen_setup import Handler
from caen_setup.Tickets.Tickets import (
    Ticket,
    SetVoltage_Ticket,
    Down_Ticket,
    GetParams_Ticket,
)

from caen_tools.utils.receipt import Receipt, ReceiptResponse
from caen_tools.utils.utils import get_timestamp


class APIMethods:
    """Contains implementations of the API methods
    of the microservice"""

    USER_TARGET_VOLTAGE = 0  # last value of voltage requested by some user

    @staticmethod
    def ticketexec(ticket: Ticket, h: Handler) -> ReceiptResponse:
        """Base ticket execution process

        Parameters
        ----------
        ticket : Ticket
            a ticket for execution
        h : Handler
            handler objects for controlling device

        Returns
        -------
        ReceiptResponse
            response on the executed ticket
        """
        ticket_response = json.loads(ticket.execute(h))
        if ticket_response["status"] is False:
            response = ReceiptResponse(
                statuscode=0, body=ticket_response["body"]["error"]
            )
            return response
        response = ReceiptResponse(statuscode=1, body=ticket_response["body"])
        return response

    @staticmethod
    def status(receipt: Receipt, h: Handler) -> Receipt:
        """Returns statuscode of the service"""
        logging.debug("Start status ticket")
        receipt.response = ReceiptResponse(statuscode=1, body={})
        return receipt

    @staticmethod
    def set_voltage(receipt: Receipt, h: Handler) -> Receipt:
        """Sets a voltage on the device

        Notes
        -----
        receipt.params must correspond SetVoltage_Ticket.type_description
        """
        logging.debug("Start set_voltage ticket")
        ticket = SetVoltage_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        if receipt.params.get("from_user", False):
            APIMethods.USER_TARGET_VOLTAGE = receipt.params["target_voltage"]
        return receipt

    @staticmethod
    def params(receipt: Receipt, h: Handler) -> Receipt:
        """Returns parameters of the device

        Notes
        -----
        receipt.params must correspond GetParams_Ticket.type_description
        """

        logging.debug("Start get params ticket")
        ticket = GetParams_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        if receipt.response.statuscode == 0:
            return receipt

        rawdata = receipt.response.body["params"]
        outdict = dict()
        for row in rawdata:
            chidx = row["channel"]["alias"]
            values = row["params"]
            outdict[chidx] = values
        receipt.response.body["params"] = outdict
        return receipt

    @staticmethod
    def down(receipt: Receipt, h: Handler) -> Receipt:
        """Turns off voltage on the device"""

        logging.debug("Start down ticket")
        ticket = Down_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        return receipt

    @staticmethod
    def get_lastuser_voltage(receipt: Receipt, h: Handler) -> Receipt:
        """Returns last voltage set by user"""

        logging.debug("Start last user set voltage ticket")
        receipt.response = ReceiptResponse(
            statuscode=1,
            body={"last_user_voltage": APIMethods.USER_TARGET_VOLTAGE},
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def wrongroute(receipt: Receipt) -> Receipt:
        """Default answer for the wrong title field in the receipt"""

        logging.debug("Start wrong_route ticket")
        receipt.response = ReceiptResponse(
            statuscode=404, body="this api method is not found"
        )
        return receipt


class APIFactory:
    """Executes input receipt"""

    apiroutes = {
        "status": APIMethods.status,
        "set_voltage": APIMethods.set_voltage,
        "params": APIMethods.params,
        "down": APIMethods.down,
        "last_user_voltage": APIMethods.get_lastuser_voltage,
    }

    @staticmethod
    def execute_receipt(receipt: Receipt, h: Handler) -> Receipt:
        """Matches a function to execute input receipt

        Parameters
        ----------
        receipt : Receipt
            input receipt for execution
        h : Handler
            handler of the device

        Returns
        -------
        Receipt
            input receipt with extra ReceiptResponse block
        """

        if receipt.title in APIFactory.apiroutes:
            return APIFactory.apiroutes[receipt.title](receipt, h)
        return APIMethods.wrongroute(receipt)
