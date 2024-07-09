"""The typical response errors"""

from caen_tools.utils.receipt import ReceiptResponse


class RResponseErrors:

    @staticmethod
    def NotFound(msg: str = "Not found error") -> ReceiptResponse:
        return ReceiptResponse(statuscode=404, body=msg)
