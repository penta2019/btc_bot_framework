from .api_ccxt import bybit
from ..base.api import ApiBase


class BybitApi(ApiBase, bybit):
    _ccxt_class = bybit

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        bybit.__init__(self, ccxt_config)
        self.load_markets()
