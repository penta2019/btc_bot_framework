import ccxt
from ..base.api import ApiBase


class BitmexApi(ApiBase, ccxt.bitmex):
    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        ccxt.bitmex.__init__(self, ccxt_config)
        self.load_markets()

        # silence linter
        self.private_get_position = getattr(self, 'private_get_position')

    def fetch_status(self, params={}):
        return ccxt.bitmex.fetch_status(self, params)  # TODO

    def fetch_position(self, symbol):
        market_id = self.market_id(symbol)
        for p in self.private_get_position():
            if p['symbol'] == market_id:
                return p['currentQty']
        return 0
