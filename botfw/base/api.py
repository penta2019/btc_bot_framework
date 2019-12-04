import logging
import inspect

from ..etc.util import run_forever_nonblocking


class ApiBase:
    MAX_API_CAPACITY = 60
    API_PER_SECOND = 1
    CCXT_SYMBOLS = {}

    def __init__(self, ccxt):
        self.log = logging.getLogger(self.__class__.__name__)
        self.ccxt = ccxt
        self.capacity = self.MAX_API_CAPACITY
        self.count = {}
        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order(self, symbol, type_, side, amount, price=0, params={}):
        return self._exec(
            self.ccxt.create_order, self.ccxt_symbol(symbol),
            type_, side, amount, price, params)

    def cancel_order(self, id_, symbol):
        return self._exec(
            self.ccxt.cancel_order, id_, self.ccxt_symbol(symbol))

    def fetch_open_orders(self, symbol):
        return self._exec(
            self.ccxt.fetch_open_orders, self.ccxt_symbol(symbol))

    def fetch_balance(self):
        return self._exec(self.ccxt.fetch_balance)

    def ccxt_symbol(self, symbol):
        return self.CCXT_SYMBOLS.get(symbol) or symbol

    def _exec(self, func, *args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except Exception:
            res = func(*args, **kwargs)  # retry once
        finally:
            func_name = inspect.stack()[1].function
            if self.log.level <= logging.DEBUG:
                self.log.debug(f'execute: {func_name} {args} {kwargs}')

            if func_name in self.count:
                self.count[func_name] += 1
            else:
                self.count[func_name] = 1

            self.capacity -= 1

        return res

    def __worker(self):
        if self.capacity < self.MAX_API_CAPACITY:
            self.capacity += self.API_PER_SECOND
