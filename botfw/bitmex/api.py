from ..base.api import ApiBase


class BitmexApi(ApiBase):
    CCXT_SYMBOLS = {
        'XBTUSD': 'BTC/USD'
    }
