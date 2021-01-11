from ..base.trade import TradeBase
from .websocket import BinanceWebsocket, BinanceFutureWebsocket
from .api import BinanceApi


class BinanceTrade(TradeBase):
    Websocket = BinanceWebsocket

    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or self.Websocket()
        self.taker_buy = float('inf')
        self.taker_sell = 0.0
        market_id = BinanceApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'{market_id.lower()}@trade', self.__on_message)

    def __on_message(self, msg):
        ts = msg['E'] / 1000
        price = float(msg['p'])
        size = float(msg['q'])
        if msg['m']:
            size *= -1

        if size > 0:
            if self.taker_sell > price:
                return
            self.taker_buy = price
        else:
            if self.taker_buy < price:
                return
            self.taker_sell = price
        self.ltp = price

        self._trigger_callback(ts, price, size)


class BinanceFutureTrade(BinanceTrade):
    Websocket = BinanceFutureWebsocket
