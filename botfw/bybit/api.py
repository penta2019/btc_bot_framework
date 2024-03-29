import ccxt
from ..base.api import ApiBase


class BybitApi(ApiBase, ccxt.bybit):
    _ccxt_class = ccxt.bybit

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        ccxt.bybit.__init__(self, ccxt_config)
        self.load_markets()

        # silence linter
        self.v2_private_get_position_list = getattr(
            self, 'v2_private_get_position_list')

    def fetch_position(self, symbol):
        market_id = self.market_id(symbol)
        res = self.v2_private_get_position_list(
            {'symbol': market_id})['result']
        return -res['size'] if res['side'] == 'Sell' else res['size']


class BybitUsdtApi(BybitApi):
    def __init__(self, ccxt_config={}):
        super().__init__(ccxt_config)

        # silence linter
        self.private_linear_get_position_list = getattr(
            self, 'private_linear_get_position_list')

    def fetch_position(self, symbol):
        market_id = self.market_id(symbol)
        res = self.private_linear_get_position_list(
            {'symbol': market_id})['result']
        print(res)
        return 0
