import ccxt
from ..base.api import ApiBase


class LiquidApi(ApiBase, ccxt.liquid):
    _ccxt_class = ccxt.liquid

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        ccxt.liquid.__init__(self, ccxt_config)
        self.load_markets()

        # silence linter
        self.private_get_trading_accounts = getattr(
            self, 'private_get_trading_accounts')

    def fetch_position(self, symbol):
        market_id = int(self.market_id(symbol))
        accounts = self.private_get_trading_accounts()
        for a in accounts:
            if a['product_id'] == market_id:
                return a['position']
        return 0.0
