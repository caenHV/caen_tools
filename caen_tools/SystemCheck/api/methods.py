"""A set of API methods for SystemCheck microservice"""

import logging
from caen_tools.utils.receipt import Receipt, ReceiptResponse
from caen_tools.utils.resperrs import RResponseErrors
from caen_tools.utils.utils import get_timestamp


class APIMethods:
    """A set of API methods of SystemCheck"""

    @staticmethod
    def status(receipt: Receipt, shared_parameters: dict, **kwargs) -> Receipt:
        """Gets status of the SysCheck"""
        logging.debug("Start status method")
        logging.debug("SHA %s", shared_parameters)
        logging.debug("SHA health %s", shared_parameters.get("health"))
        logging.debug("SHA relax %s", shared_parameters.get("relax"))
        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                health=dict(
                    enable=shared_parameters.get("health").get("enable"),
                ),
                autopilot=dict(
                    enable=shared_parameters.get("relax").get("enable"),
                ),
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def autopilot_enable(
        receipt: Receipt, shared_parameters: dict, **kwargs
    ) -> Receipt:
        """Gets interlock follow status"""

        logging.debug("Start autopilot_enable receipt")
        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                interlock_follow=(
                    shared_parameters.get("relax").get("enable")
                    and shared_parameters.get("reducer").get("enable")
                )
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def set_autopilot(receipt: Receipt, shared_parameters: dict, **kwargs) -> Receipt:
        """Sets new state of interlock follow"""

        logging.info("Set interlock_follow to %s", receipt.params)
        shared_parameters["relax"]["enable"] = bool(receipt.params["value"])
        shared_parameters["reducer"]["enable"] = bool(receipt.params["value"])

        logging.info("new par %s", shared_parameters["interlock"]["enable"])
        shared_parameters["relax"]["target_voltage"] = float(
            receipt.params["target_voltage"]
        )
        shared_parameters["reducer"]["target_voltage"] = float(
            receipt.params["target_voltage"]
        )

        logging.info("new par %s", shared_parameters["relax"]["enable"])
        return APIMethods.autopilot_enable(receipt, shared_parameters, **kwargs)

    @staticmethod
    def wrongroute(receipt: Receipt, **kwargs) -> Receipt:
        """Default answer for the wrong title field in the receipt"""

        logging.debug("Start wrong_route ticket")
        receipt.response = RResponseErrors.NotFound(msg="API route is not found")
        return receipt
