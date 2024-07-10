"""Defines API methods for DeviceBackend microservice"""

import json
from caen_setup import Handler
from caen_setup.Tickets.Tickets import (
    Ticket,
    SetVoltage_Ticket,
    Down_Ticket,
    GetParams_Ticket,
)

from caen_tools.utils.receipt import Receipt, ReceiptResponse


class APIMethods:
    """Contains implementations of the API methods
    of the microservice"""

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
        receipt.response = ReceiptResponse(statuscode=1, body={})
        return receipt

    @staticmethod
    def set_voltage(receipt: Receipt, h: Handler) -> Receipt:
        """Sets a voltage on the device

        Notes
        -----
        receipt.params must correspond SetVoltage_Ticket.type_description
        """
        ticket = SetVoltage_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        return receipt

    @staticmethod
    def params(receipt: Receipt, h: Handler) -> Receipt:
        """Returns parameters of the device

        Notes
        -----
        receipt.params must correspond GetParams_Ticket.type_description
        """

        ticket = GetParams_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        rawdict = receipt.response.body["params"]
        outdict = dict()
        for key in rawdict:
            keydict = json.loads(key.replace("\\", ""))
            board = list(keydict["board_info"].keys())[0]
            conet = keydict["board_info"][board]["conet"]
            link = keydict["board_info"][board]["link"]
            chnum = keydict["channel_num"]
            channel_id = f"{board}_{conet}_{link}_{chnum}"
            outdict[channel_id] = rawdict[key]
        receipt.response.body["params"] = outdict
        return receipt

    @staticmethod
    def down(receipt: Receipt, h: Handler) -> Receipt:
        """Turns off voltage on the device"""
        ticket = Down_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        return receipt

    @staticmethod
    def wrongroute(receipt: Receipt) -> Receipt:
        """Default answer for the wrong title field in the receipt"""
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
