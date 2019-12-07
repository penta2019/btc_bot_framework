from ..base.orderbook import OrderbookBase
from .websocket import BinanceWebsocket


class BinanceOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None, future=False):
        super().__init__()
        self.symbol = symbol
        self.ch = f'{self.symbol}@depth'
        self.ws = ws or BinanceWebsocket(future=future)
        self.ws.add_after_open_callback(self.__after_open)

    def __after_open(self):
        self.init()
        self.ws.subscribe(self.ch, self.__on_message)

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
