import ccxt
from ..base.api import ApiBase
from ..etc.util import decimal_add

ccxt_bitflyer = ccxt.bitflyer()
ccxt_bitflyer.load_markets()


class BitflyerApi(ApiBase, ccxt.bitflyer):
    def __init__(self, ccxt_config):
        ApiBase.__init__(self)
        ccxt.bitflyer.__init__(self, ccxt_config)
        self.load_markets()

        # silence linter
        self.public_get_getboardstate = getattr(
            self, 'public_get_getboardstate')
        self.private_get_getpositions = getattr(
            self, 'private_get_getpositions')

    def fetch_status(self, params={'product_code': 'FX_BTC_JPY'}):
        res = self.public_get_getboardstate(params)
        status = 'ok' if res['state'] == 'RUNNING' else 'shutdown'
        return {
            'status': status,  # 'ok', 'shutdown', 'error', 'maintenance'
            'updated': None,
            'eta': None,
            'url': None,
        }

    def fetch_position(self, symbol):
        market_id = self.market_id(symbol)
        positions = self.private_get_getpositions({'product_code': market_id})
        total = 0
        for pos in positions:
            size = -pos['size'] if pos['side'] == 'SELL' else pos['size']
            total = decimal_add(total, size)
        return total

    def fetch_collateral(self):
        func = getattr(self, 'private_get_getcollateral')
        return func()

    def cancel_all_order(self, symbol):
        market_id = self.market_id(symbol)
        func = getattr(self, 'private_post_cancelallchildorders')
        return func({'product_code': market_id})
