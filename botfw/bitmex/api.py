import ccxt
from ..base.api import ApiBase

_ccxt_bitmex = None


def ccxt_bitmex():
    global _ccxt_bitmex
    if _ccxt_bitmex:
        return _ccxt_bitmex

    _ccxt_bitmex = ccxt.bitmex()
    _ccxt_bitmex.load_markets()
    return _ccxt_bitmex


class BitmexApi(ApiBase, ccxt.bitmex):
    def __init__(self, ccxt_config):
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
