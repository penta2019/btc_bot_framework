import ccxt
from ..base.api import ApiBase


class BitbankApi(ApiBase, ccxt.bitbank):
    _ccxt_class = ccxt.bitbank

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        ccxt.bitbank.__init__(self, ccxt_config)
        self.load_markets()
