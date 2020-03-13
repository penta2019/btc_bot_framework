from ..base.orderbook import OrderbookBase
from .websocket import GmocoinWebsocket
from .api import GmocoinApi


class GmocoinOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or GmocoinWebsocket()

        market_id = GmocoinApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(('orderbooks', market_id), self.__on_message)

    def init(self):
        self.ls_bids, self.ls_asks = [], []

    def bids(self):
        return self.ls_bids

    def asks(self):
        return self.ls_asks

    def __on_message(self, msg):
        bids, asks = [], []
        for b in msg['bids']:
            bids.append((float(b['price']), float(b['size'])))
        for a in msg['asks']:
            asks.append((float(a['price']), float(a['size'])))
        self.ls_bids, self.ls_asks = bids, asks

        self._trigger_callback()
