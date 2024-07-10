"""The typical response errors"""

from caen_tools.utils.receipt import ReceiptResponse


class RResponseErrors:
    """A number of ReceiptResponses for common error cases"""

    @staticmethod
    def NotFound(msg: str = "Not found error") -> ReceiptResponse:
        """Response when something not found (route or method)"""
        return ReceiptResponse(statuscode=404, body=msg)

    @staticmethod
    def GatewayTimeout(msg: str = "Server error: Gateway Timeout") -> ReceiptResponse:
        """Response when waiting time exeeded (for example)"""
        return ReceiptResponse(statuscode=504, body=msg)
