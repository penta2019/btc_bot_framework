import ccxt
from ..base.api import ApiBase

ccxt_binance = ccxt.binance()
ccxt_binance.load_markets()


class BinanceApi(ApiBase, ccxt.binance):
    def __init__(self, ccxt_config):
        ApiBase.__init__(self)
        ccxt.binance.__init__(self, ccxt_config)
        self.future = self.options.get('defaultType') == 'future'

    def listen_key(self, method='POST'):
        # POST: create new
        # PUT: keep alive (every 30 minutes)
        # DELETE: close
        if self.future:
            return self.request('listenKey', 'fapiPrivate', method)
        else:
            return self.request('userDataStream', 'v3', method)
