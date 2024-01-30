"""Implementation of the special dictioary to store response information
"""

import asyncio
from collections import OrderedDict


class ResponseDict(OrderedDict):
    """Class to store responsed data"""

    def __init__(self, maxsize: int = 10):
        super().__init__()
        self.__maxsize = maxsize

    def __setitem__(self, key, value):
        """
        Parameters
        ----------
        key: str
            timestamp of request
        value: str
            string response
        """
        super().__setitem__(key, value)
        self.move_to_end(key)
        self.__remove_tail()

    def __remove_tail(self):
        """Removes redundant items"""
        while len(self) > self.__maxsize:
            self.popitem()
        return

    async def popwaiting(self, key, ntryings: int = 10):
        """Pops dict item with key `key` for n tryings 

        Raises
        ------
        KeyError
            raising when key is not found
        """
        sleepcycle = 0.25
        for _ in range(ntryings):
            try:
                resp = self.pop(key)
                return resp
            except KeyError:
                await asyncio.sleep(sleepcycle)
        return None
