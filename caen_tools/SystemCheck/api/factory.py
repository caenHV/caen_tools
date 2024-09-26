from caen_tools.SystemCheck.api import APIMethods
from caen_tools.utils.receipt import Receipt


class APIFactory:
    """Executes input receipt"""

    apiroutes = {
        "status": APIMethods.status,
        "follow_ilock": APIMethods.is_interlock_follow,
        "set_follow_ilock": APIMethods.set_ilock_follow,
    }

    @staticmethod
    def execute_receipt(receipt: Receipt, shared_parameters: dict) -> Receipt:
        """Matches a function to execute input receipt

        Parameters
        ----------
        receipt : Receipt
            input receipt for execution
        shared_parameters : dict
            shared memory that keeps status information

        Returns
        -------
        Receipt
            input receipt with extra ReceiptResponse block
        """

        if receipt.title in APIFactory.apiroutes:
            return APIFactory.apiroutes[receipt.title](
                receipt=receipt, shared_parameters=shared_parameters
            )
        return APIMethods.wrongroute(receipt)
