from ..base.orderbook import OrderbookBase
from .websocket import BinanceWebsocket, BinanceFutureWebsocket
from .api import BinanceApi


class BinanceOrderbook(OrderbookBase):
    Websocket = BinanceWebsocket

    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or self.Websocket()
        self.ws.add_after_open_callback(self.init)
        market_id = BinanceApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'{market_id.lower()}@depth', self.__on_message)

    def __on_message(self, msg):
        self.__update(self.sd_bids, msg['b'], -1)
        self.__update(self.sd_asks, msg['a'], 1)
        self._trigger_callback()

    def __update(self, sd, d, sign):
        for i in d:
            p, s = float(i[0]), float(i[1])
            if s == 0:
                sd.pop(p * sign, None)
            else:
                sd[p * sign] = [p, s]


class BinanceFutureOrderbook(BinanceOrderbook):
    Websocket = BinanceFutureWebsocket
