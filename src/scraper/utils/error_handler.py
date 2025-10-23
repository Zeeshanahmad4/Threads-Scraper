import time
from typing import Callable, Tuple
def retry(exceptions: Tuple[Exception, ...], tries: int = 3, delay: float = 0.5, backoff: float = 2.0) -> Callable:
    """
    Simple retry decorator with exponential backoff.
    """
    def deco(fn: Callable) -> Callable:
        def wrapped(*args, **kwargs):
            _tries = max(1, int(tries))
            _delay = max(0.0, float(delay))
            for attempt in range(1, _tries + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt >= _tries:
                        raise
                    time.sleep(_delay)
                    _delay *= backoff
            # Should not reach here
            return fn(*args, **kwargs)
        return wrapped
    return deco
