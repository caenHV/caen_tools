"""The typical response errors"""

from caen_tools.utils.receipt import ReceiptResponse, ReceiptResponseError


class RResponseErrors:
    """A number of ReceiptResponses for common error cases"""

    @staticmethod
    def NotFound(msg: str = "Not found error") -> ReceiptResponse:
        """Response when something not found (route or method)"""
        return ReceiptResponseError(statuscode=404, body=msg)

    @staticmethod
    def GatewayTimeout(msg: str = "Server error: Gateway Timeout") -> ReceiptResponse:
        """Response when waiting time exeeded (for example)"""
        return ReceiptResponseError(statuscode=503, body=msg)

    @staticmethod
    def ForbiddenMethod(
        msg: str = "Usage of the method is prohibited",
    ) -> ReceiptResponse:
        """Response when usage of the some API method is forbidden"""
        return ReceiptResponseError(statuscode=403, body=msg)
