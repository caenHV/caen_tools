"""The typical response errors"""

from caen_tools.utils.receipt import ReceiptResponse, ReceiptResponseError
from caen_tools.utils.statuscodes import StatusCode


class RResponseErrors:
    """A number of ReceiptResponses for common error cases"""

    @staticmethod
    def NotFound(msg: str = "Not found error") -> ReceiptResponse:
        """Response when something not found (route or method)"""
        return ReceiptResponseError(statuscode=StatusCode.NOT_FOUND, body=msg)

    @staticmethod
    def NotImplemented(msg: str = "Not implemented method") -> ReceiptResponse:
        """Response when something not implemented right now (route or method)"""
        return ReceiptResponseError(statuscode=StatusCode.NOT_ALLOWED, body=msg)

    @staticmethod
    def GatewayTimeout(msg: str = "Server error: Gateway Timeout") -> ReceiptResponse:
        """Response when waiting time exeeded (for example)"""
        return ReceiptResponseError(statuscode=StatusCode.UNAVAILABLE, body=msg)

    @staticmethod
    def ForbiddenMethod(
        msg: str = "Usage of the method is prohibited",
    ) -> ReceiptResponse:
        """Response when usage of the some API method is forbidden"""
        return ReceiptResponseError(statuscode=StatusCode.FORBIDDEN, body=msg)
