from dataclasses import dataclass, field
from typing import Union

import json
import dataclasses
from caen_tools.utils.utils import get_timestamp


@dataclass
class ReceiptResponse:
    """Defines a structure of the receipt response"""

    statuscode: int
    body: Union[str, dict]
    timestamp: int = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = get_timestamp()


@dataclass
class Receipt:
    """Class for keeping receipts"""

    sender: str
    executor: str
    title: str
    params: dict
    timestamp: int = None
    response: ReceiptResponse = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = get_timestamp()


class ReceiptJSONEncoder(json.JSONEncoder):
    """JSON Encoder for the receipt dataclass"""

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class ReceiptJSONDecoder(json.JSONDecoder):
    """JSON Decoder for the receipt dataclass"""

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        """Decoder of the dictionary"""

        if ("sender" in dct) and ("executor" in dct):
            response_dict = dct.pop("response", None)
            response = (
                ReceiptResponse(**response_dict) if response_dict is not None else None
            )
            return Receipt(response=response, **dct)
        return dct
