import json

from ..base.orderbook import OrderbookBase
from .websocket import LiquidWebsocket


class LiquidOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or LiquidWebsocket()

        market_id = self.symbol.replace('/', '').lower()
        self.ch_buy = f'price_ladders_cash_{market_id}_buy'
        self.ch_sell = f'price_ladders_cash_{market_id}_sell'
        self.ws.subscribe(self.ch_buy, self.__on_message)
        self.ws.subscribe(self.ch_sell, self.__on_message)

    def init(self):
        self.ls_bids, self.ls_asks = [], []

    def bids(self):
        return self.ls_bids

    def asks(self):
        return self.ls_asks

    def __on_message(self, msg):
        ob = []
        for d in json.loads(msg['data']):
            ob.append((float(d[0]), float(d[1])))

        ch = msg['channel']
        if ch == self.ch_buy:
            self.ls_bids = ob
        elif ch == self.ch_sell:
            self.ls_asks = ob
        else:
            self.log.error(f'Unknown channel {ch}')

        self._trigger_callback()
