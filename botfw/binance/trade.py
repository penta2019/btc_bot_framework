from ..base.trade import TradeBase
from .websocket import BinanceWebsocket, BinanceFutureWebsocket
from .api import BinanceApi


class BinanceTrade(TradeBase):
    Websocket = BinanceWebsocket

    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or self.Websocket()
        market_id = BinanceApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'{market_id.lower()}@trade', self.__on_message)

    def __on_message(self, msg):
        ts = msg['E'] / 1000
        price = float(msg['p'])
        size = float(msg['q'])
        if msg['m']:
            size *= -1
        self.ltp = price

        self._trigger_callback(ts, price, size)


class BinanceFutureTrade(BinanceTrade):
    Websocket = BinanceFutureWebsocket
