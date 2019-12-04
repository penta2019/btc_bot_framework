from ..base.api import ApiBase


class BitflyerApi(ApiBase):
    def fetch_boardstate(self, symbol):
        func = getattr(self.ccxt, 'public_get_getboardstate')
        return self._exec(func, {'product_code': symbol})

    def fetch_health(self, symbol):
        func = getattr(self.ccxt, 'public_get_gethealth')
        return self._exec(func, symbol)

    def fetch_collateral(self):
        func = getattr(self.ccxt, 'private_get_getcollateral')
        return self._exec(func)

    def fetch_positions(self, symbol):
        func = getattr(self.ccxt, 'private_get_getpositions')
        return self._exec(func, {'product_code': symbol})

    def cancel_all_order(self, symbol):
        func = getattr(self.ccxt, 'private_post_cancelallchildorders')
        self._exec(func, {'product_code': symbol})
