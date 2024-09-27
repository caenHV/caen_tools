"""A set of API methods for SystemCheck microservice"""

import logging
from caen_tools.utils.receipt import Receipt, ReceiptResponse
from caen_tools.utils.utils import get_timestamp


class APIMethods:
    """A set of API methods of SystemCheck"""

    @staticmethod
    def status(receipt: Receipt, shared_parameters: dict, **kwargs) -> Receipt:
        """Gets status of the SysCheck"""
        logging.debug("Start status method")

        last_check_timestamp = shared_parameters["health"]["last_check"]

        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                health = shared_parameters["health"],
                autopilot = shared_parameters["interlock"],
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def is_interlock_follow(
        receipt: Receipt, shared_parameters: dict, **kwargs
    ) -> Receipt:
        """Gets interlock follow status"""

        logging.debug("Start is_interlock_follow receipt")
        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                interlock_follow=shared_parameters.get("interlock").get("enable")
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def set_ilock_follow(
        receipt: Receipt, shared_parameters: dict, **kwargs
    ) -> Receipt:
        """Sets new state of interlock follow"""

        logging.info("Set interlock_follow to %s", receipt.params)
        shared_parameters["interlock"]["enable"] = bool(receipt.params["value"])
        logging.info("new par %s", shared_parameters["interlock"]["enable"])
        shared_parameters["interlock"]["target_voltage"] = float(
            receipt.params["target_voltage"]
        )
        logging.info("new par %s", shared_parameters["interlock"]["enable"])
        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                interlock_follow=shared_parameters.get("interlock").get("enable"),
                target_voltage=shared_parameters.get("interlock").get("target_voltage"),
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def wrongroute(receipt: Receipt, **kwargs) -> Receipt:
        """Default answer for the wrong title field in the receipt"""

        logging.debug("Start wrong_route ticket")
        receipt.response = ReceiptResponse(
            statuscode=404, body="this api method is not found"
        )
        return receipt
