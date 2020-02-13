import ccxt
from ..base.api import ApiBase


class LiquidApi(ApiBase, ccxt.liquid):
    _ccxt_class = ccxt.liquid

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        ccxt.liquid.__init__(self, ccxt_config)
        self.load_markets()
