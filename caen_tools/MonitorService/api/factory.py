"""Implementation of the Monitor API"""

import logging
from caen_tools.utils.receipt import Receipt, ReceiptResponse
from .monclass import Monitor


class APIMethods:
    """Contains implementations of the API methods
    of the microservice"""

    @staticmethod
    def status(receipt: Receipt, monitor: Monitor):
        """Returns status of the microservice"""
        receipt.response = ReceiptResponse(statuscode=1, body={})
        return receipt

    @staticmethod
    def execute_send(receipt: Receipt, monitor: Monitor):
        """Sends device parameters in Monitor.
        Monitor writes them in the DB and returns {}"""
        response = monitor.send_params(
            receipt.params, measurement_time=receipt.timestamp
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body={},
        )
        return receipt

    @staticmethod
    def execute_send_status(receipt: Receipt, monitor: Monitor):
        """Sends device status in the Monitor.
        Monitor writes them in the DB and returns {}"""
        response = monitor.send_status(
            receipt.params["is_ok"],
            receipt.params["description"],
            timestamp=receipt.timestamp,
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body={},
        )
        return receipt

    @staticmethod
    def execute_get(receipt: Receipt, monitor: Monitor):
        """Gets device parameters from Monitor"""
        response = monitor.get_params(
            receipt.params["start_time"], receipt.params["end_time"]
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body=(
                response["params"]
                if response["is_ok"]
                else "Something is wrong in the DB. No rows selected."
            ),
        )
        return receipt

    @staticmethod
    def execute_get_status(receipt: Receipt, monitor: Monitor):
        """Gets device status from the Monitor"""
        response = monitor.get_status(
            receipt.params["start_time"], receipt.params["end_time"]
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body=(
                response["status"]
                if response["is_ok"]
                else "Something is wrong in the DB. No rows selected."
            ),
        )
        return receipt

    @staticmethod
    def execute_get_n_downs(receipt: Receipt, monitor: Monitor):
        """Gets number of downs in the queried time window status from the Monitor"""
        response = monitor.get_n_downs(
            receipt.params["start_time"], receipt.params["end_time"]
        )
        receipt.response = ReceiptResponse(
            statuscode=1 if response["is_ok"] else 0,
            body=(
                response["n_downs"]
                if response["is_ok"]
                else "Something is wrong in the DB. No rows selected."
            ),
        )
        return receipt

    @staticmethod
    def wrongroute(receipt: Receipt) -> Receipt:
        """Default answer for the wrong title field in the receipt"""
        receipt.response = ReceiptResponse(
            statuscode=404, body="this api method is not found"
        )
        return receipt


class APIFactory:
    """Matches receipts with the following routes"""

    apiroutes = {
        "status": APIMethods.status,
        "send_params": APIMethods.execute_send,
        "send_status": APIMethods.execute_send_status,
        "get_params": APIMethods.execute_get,
        "get_status": APIMethods.execute_get_status,
        "get_n_downs": APIMethods.execute_get_n_downs,
    }

    @staticmethod
    def execute_receipt(receipt: Receipt, monitor: Monitor) -> Receipt:
        """Matches a function to execute input receipt"""

        if receipt.title in APIFactory.apiroutes:
            try:
                return APIFactory.apiroutes[receipt.title](receipt, monitor)
            except Exception:
                logging.error("Not processed %s", receipt, exc_info=True)
        return APIMethods.wrongroute(receipt)
