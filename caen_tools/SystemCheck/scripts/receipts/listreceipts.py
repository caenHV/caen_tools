import logging
from caen_tools.utils.receipt import Receipt


class Services:
    """List of services"""

    MONITOR = "monitor"
    DEVBACK = "devback"


class PreparedReceipts:

    @staticmethod
    def set_voltage(sender: str, target_voltage: float) -> Receipt:
        """Sets voltage on device"""

        logging.debug("Ask for receipt set_voltage")
        return Receipt(
            sender=sender,
            executor=Services.DEVBACK,
            title="set_voltage",
            params={"target_voltage": target_voltage},
        )

    @staticmethod
    def get_voltage(sender: str) -> Receipt:
        """Gets current voltage multiplier"""

        logging.debug("Current voltage multiplier")
        return Receipt(
            sender=sender,
            executor=Services.DEVBACK,
            title="get_voltage",
            params={},
        )

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
    def down(sender: str) -> Receipt:
        """Downs voltage"""
        logging.debug("Ask for receipt devback/down")
        return Receipt(
            sender=sender,
            executor=Services.DEVBACK,
            title="down",
            params={},
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
