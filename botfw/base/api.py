import logging
import collections
import inspect

from ..etc.util import run_forever_nonblocking


class ApiBase:
    def __init__(self, max_capacity=100):
        self.log = logging.getLogger(self.__class__.__name__)
        self.max_capacity = max_capacity
        self.capacity = max_capacity
        self.count = collections.defaultdict(lambda: 0)

    def _exec(self, func, *args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except Exception:
            res = func(*args, **kwargs)  # retry once
        finally:
            func_name = inspect.stack()[1].function
            if self.log.level <= logging.DEBUG:
                self.log.debug(f'execute: {func_name} {args} {kwargs}')
            self.count[func_name] += 1
            self.capacity -= 1

        return res

    def __worker(self):
        if self.capacity < self.max_capacity:
            self.capacity += 1
