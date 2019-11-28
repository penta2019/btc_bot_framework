import collections
import inspect

from ..etc.util import *

MAX_API_CAPACITY = 60


class BitflyerApi:
    def __init__(self, ccxt):
        self.log = logging.getLogger(self.__class__.__name__)
        self.ccxt = ccxt
        self.capacity = MAX_API_CAPACITY
        self.count = collections.defaultdict(lambda: 0)

        run_forever_nonblocking(self.__worker, self.log, 1)

    def fetch_boardstate(self, symbol):
        func = getattr(self.ccxt, 'public_get_getboardstate')
        return self._exec(func, {'product_code': symbol})

    def fetch_health(self, symbol):
        func = getattr(self.ccxt, 'public_get_gethealth')
        return self._exec(func, symbol)

    def fetch_balance(self):
        return self._exec(self.ccxt.fetch_balance)

    def fetch_collateral(self):
        func = getattr(self.ccxt, 'private_get_getcollateral')
        return self._exec(func)

    def fetch_positions(self, symbol):
        func = getattr(self.ccxt, 'private_get_getpositions')
        return self._exec(func, {'product_code': symbol})

    def fetch_open_orders(self, symbol):
        return self._exec(self.ccxt.fetch_open_orders, symbol)

    def create_order(self, symbol, type_, side, amount, price=0,
                     minute_to_expire=43200, time_in_force='GTC'):
        return self._exec(
            self.ccxt.create_order, symbol, type_, side, amount, price,
            params={
                'minute_to_expire': minute_to_expire,
                'time_in_foce': time_in_force,
            })

    def cancel_order(self, id_, symbol):
        return self._exec(self.ccxt.cancel_order, id_, symbol)

    def cancel_all_order(self, symbol):
        func = getattr(self.ccxt, 'private_post_cancelallchildorders')
        self._exec(func, {'product_code': symbol})

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
        if self.capacity < MAX_API_CAPACITY:
            self.capacity += 1
