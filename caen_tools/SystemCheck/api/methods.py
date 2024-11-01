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
        logging.debug("Shared memory / health %s", shared_parameters.get("health"))
        logging.debug("Shared memory / relax %s", shared_parameters.get("relax"))
        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                health=dict(
                    enable=shared_parameters.get("health").get("enable"),
                ),
                autopilot=dict(
                    enable=all(
                        [
                            shared_parameters[script_name]["enable"]
                            for script_name in shared_parameters["autopilot"]["run"]
                        ]
                    ),
                    runscripts=",".join(shared_parameters["autopilot"]["run"]),
                    interlock_follow=all(
                        [
                            shared_parameters[script_name]["enable"]
                            for script_name in shared_parameters["autopilot"]["run"]
                        ]
                    ),
                    # FIXME: Костыль!!! Нужно иначе хранить target_voltage
                    target_voltage=shared_parameters["relax"]["target_voltage"],
                ),
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def autopilot_enable(
        receipt: Receipt, shared_parameters: dict, **kwargs
    ) -> Receipt:
        """Gets autopilot status"""

        logging.debug("Start autopilot_enable receipt")
        receipt.response = ReceiptResponse(
            statuscode=1,
            body=dict(
                interlock_follow=all(
                    [
                        shared_parameters[script_name]["enable"]
                        for script_name in shared_parameters["autopilot"]["run"]
                    ]
                )
            ),
            timestamp=get_timestamp(),
        )
        return receipt

    @staticmethod
    def set_autopilot(receipt: Receipt, shared_parameters: dict, **kwargs) -> Receipt:
        """Sets new state of interlock follow"""

        logging.info("Set autopilot value to %s", receipt.params)
        for script_name in shared_parameters["autopilot"]["run"]:
            shared_parameters[script_name]["enable"] = bool(receipt.params["value"])

            shared_parameters[script_name]["target_voltage"] = float(
                receipt.params["target_voltage"]
            )

            logging.debug("new par %s", shared_parameters[script_name]["enable"])
        return APIMethods.autopilot_enable(receipt, shared_parameters, **kwargs)

    @staticmethod
    def wrongroute(receipt: Receipt, **kwargs) -> Receipt:
        """Default answer for the wrong title field in the receipt"""

        logging.debug("Start wrong_route ticket")
        receipt.response = RResponseErrors.NotFound(msg="API route is not found")
        return receipt
