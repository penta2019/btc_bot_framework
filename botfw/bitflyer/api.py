import ccxt
from ..base.api import ApiBase
from ..etc.util import decimal_add


class BitflyerApi(ApiBase, ccxt.bitflyer):
    _ccxt_class = ccxt.bitflyer

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        ccxt.bitflyer.__init__(self, ccxt_config)
        self.load_markets()

        # silence linter
        self.public_get_getboardstate = getattr(
            self, 'public_get_getboardstate')
        self.private_get_getpositions = getattr(
            self, 'private_get_getpositions')
        self.private_post_cancelallchildorders = getattr(
            self, 'private_post_cancelallchildorders')
        self.private_get_getcollateral = getattr(
            self, 'private_get_getcollateral')

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
        return self.private_get_getcollateral()

    def cancel_all_order(self, symbol):
        market_id = self.market_id(symbol)
        return self.private_post_cancelallchildorders(
            {'product_code': market_id})
