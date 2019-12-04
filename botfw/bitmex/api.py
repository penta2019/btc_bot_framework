from ..base.api import ApiBase

MAX_API_CAPACITY = 60

ccxt_symbol = {
    'XBTUSD': 'BTC/USD'
}


class BitmexApi(ApiBase):
    def __init__(self, ccxt):
        super().__init__(MAX_API_CAPACITY)
        self.ccxt = ccxt

    def create_order(self, symbol, type_, side, amount, price=0):
        symbol = ccxt_symbol[symbol]
        return self._exec(
            self.ccxt.create_order, symbol, type_, side, amount, price)

    def cancel_order(self, id_, symbol):
        symbol = ccxt_symbol[symbol]
        return self._exec(self.ccxt.cancel_order, id_, symbol)
