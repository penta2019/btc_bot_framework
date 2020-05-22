import ccxt
from ..base.api import ApiBase


class BinanceApi(ApiBase, ccxt.binance):
    FUTURE = False
    _ccxt_class = ccxt.binance

    def __init__(self, ccxt_config={}):
        if self.FUTURE:
            ccxt_config.setdefault('options', {})['defaultType'] = 'future'
        ApiBase.__init__(self)
        ccxt.binance.__init__(self, ccxt_config)
        self.load_markets()

        # silence linter
        self.fapiPrivate_get_positionrisk = getattr(
            self, 'fapiPrivate_get_positionrisk')

    def fetch_position(self, symbol):
        market_id = self.market_id(symbol)
        positions = self.fapiPrivate_get_positionrisk()
        for pos in positions:
            if pos['symbol'] == market_id:
                return float(pos['positionAmt'])
        raise Exception('symbol not found')

    def websocket_key(self, method='POST', listen_key=None):
        # POST: create new
        # PUT: keep alive (every 30 minutes, listen_key is needed)
        # DELETE: close (listen_key is needed)
        params = {}
        if listen_key:
            params['listenKey'] = listen_key

        if self.FUTURE:
            return self.request('listenKey', 'fapiPrivate', method, params)
        else:
            return self.request('userDataStream', 'v3', method, params)


class BinanceFutureApi(BinanceApi):
    FUTURE = True
