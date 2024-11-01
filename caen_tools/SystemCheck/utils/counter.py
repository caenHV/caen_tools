from bisect import bisect_left
from functools import reduce
from time import time

class CounterTTL:
    """Time expiring counter
    
    Parameters
    ----------
    expiring_time: int
        value expiration time, in seconds    
    """

    def __init__(self, expiring_time: int):
        self._ttl = expiring_time
        self._values = []
    
    def increment(self, value: int) -> None:
        """Increments counter by the given value"""
        self._values.append((time(), value))
    
    def _update(self):
        t_start = time() - self._ttl
        idx = bisect_left(self._values, t_start, key=lambda x: x[0])
        self._values = self._values[idx:]
    
    @property
    def count(self) -> int:
        """Returns count now"""
        self._update()
        return reduce(lambda x, y: x + y[1], self._values, 0)

