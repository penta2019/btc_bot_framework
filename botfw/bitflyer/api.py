import ccxt
from ..base.api import ApiBase


class BitflyerApi(ApiBase, ccxt.bitflyer):
    def __init__(self, config):
        ApiBase.__init__(self)
        ccxt.bitflyer.__init__(self, config)

    def fetch_boardstate(self, symbol):
        func = getattr(self, 'public_get_getboardstate')
        return func({'product_code': symbol})

    def fetch_health(self, symbol):
        func = getattr(self, 'public_get_gethealth')
        return func(symbol)

    def fetch_collateral(self):
        func = getattr(self, 'private_get_getcollateral')
        return func()

    def fetch_positions(self, symbol):
        func = getattr(self, 'private_get_getpositions')
        return func({'product_code': symbol})

    def cancel_all_order(self, symbol):
        func = getattr(self, 'private_post_cancelallchildorders')
        return func({'product_code': symbol})
