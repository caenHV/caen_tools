import logging

from caen_tools.utils.receipt import Receipt
from .utils import Services


class PreparedReceipts:
    """A set of prepared receipts for monitor worker easy usage"""

    @staticmethod
    def get_params(sender: str, parameters: list | None = None) -> Receipt:
        """Gets parameters from device backend"""

        logging.debug("Ask for receipt devback/params")
        return Receipt(
            sender=sender,
            executor=Services.DEVBACK,
            title="params",
            params={"select_params": parameters},
        )

    @staticmethod
    def put2mon(sender: str, params: dict) -> Receipt:
        """Puts parameters into monitor"""
        logging.debug("Ask for receipt mon/send_params")
        return Receipt(
            sender=sender,
            executor=Services.MONITOR,
            title="send_params",
            params={"params": params},
        )
