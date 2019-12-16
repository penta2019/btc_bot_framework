import ccxt
from ..base.api import ApiBase
from ..etc.util import decimal_sum

ccxt_bitflyer = ccxt.bitflyer()
ccxt_bitflyer.load_markets()


class BitflyerApi(ApiBase, ccxt.bitflyer):
    def __init__(self, ccxt_config):
        ApiBase.__init__(self)
        ccxt.bitflyer.__init__(self, ccxt_config)

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

    def get_total_position(self, symbol):
        total = 0
        for pos in self.fetch_positions(symbol):
            size = -pos['size'] if pos['side'] == 'SELL' else pos['size']
            total = decimal_sum(total, size)
        return total
