import json
from caen_setup import Handler
from caen_setup.Tickets.Tickets import Ticket, SetVoltage_Ticket, Down_Ticket, GetParams_Ticket

from caen_tools.utils.receipt import Receipt, ReceiptResponse


class APIMethods:

    @staticmethod
    def ticketexec(ticket: Ticket, h: Handler) -> ReceiptResponse:
        ticket_response = json.loads(ticket.execute(h))
        if ticket_response['status'] is False:
            response = ReceiptResponse(
                statuscode=0, body=ticket_response['body']['error']
            )
            return response
        response = ReceiptResponse(
            statuscode=1, body=ticket_response["body"]
        )
        return response


    @staticmethod
    def status(receipt: Receipt, h: Handler) -> Receipt:
        receipt.response = ReceiptResponse(statuscode=1, body={})
        return receipt

    @staticmethod
    def set_voltage(receipt: Receipt, h: Handler) -> Receipt:
        ticket = SetVoltage_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        return receipt

    @staticmethod
    def params(receipt: Receipt, h: Handler) -> Receipt:
        ticket = GetParams_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        rawdict = receipt.response.body['params']
        outdict = dict()
        for key in rawdict:
            keydict = json.loads(key.replace('\\', ''))
            board = list(keydict['board_info'].keys())[0]
            conet = keydict['board_info'][board]['conet']
            link = keydict['board_info'][board]['link']
            chnum = keydict['channel_num']
            channel_id = f"{board}_{conet}_{link}_{chnum}"
            outdict[channel_id] = rawdict[key]
        receipt.response.body['params'] = outdict
        return receipt

    @staticmethod
    def down(receipt: Receipt, h: Handler) -> Receipt:
        ticket = Down_Ticket(receipt.params)
        receipt.response = APIMethods.ticketexec(ticket, h)
        return receipt

    @staticmethod
    def wrongroute(receipt: Receipt) -> Receipt:
        receipt.response = ReceiptResponse(
            statuscode=404, body="this api method is not found"
        )
        return receipt


class APIFactory:

    apiroutes = {
        "status": APIMethods.status, 
        "set_voltage": APIMethods.set_voltage, 
        "params": APIMethods.params,
        "down": APIMethods.down,
    }

    @staticmethod
    def execute_receipt(receipt: Receipt, h: Handler) -> Receipt:
        """Matches a function to execute input receipt"""

        if receipt.title in APIFactory.apiroutes:
            return APIFactory.apiroutes[receipt.title](receipt, h)
        return APIMethods.wrongroute(receipt)
