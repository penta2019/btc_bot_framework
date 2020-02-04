from ..base.orderbook import OrderbookBase
from .websocket import GmocoinWebsocket
from .api import GmocoinApi


class GmocoinOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or GmocoinWebsocket()
        self.ws.add_after_open_callback(self.__after_open)

    def init(self):
        self.ls_bids, self.ls_asks = [], []

    def bids(self):
        return self.ls_bids

    def asks(self):
        return self.ls_asks

    def __after_open(self):
        market_id = GmocoinApi.ccxt_instance().market_id(self.symbol)
        ch = {'channel': 'orderbooks', 'symbol': market_id}
        self.ws.subscribe(ch, self.__on_message)

    def __on_message(self, msg):
        bids, asks = [], []
        for b in msg['bids']:
            bids.append((float(b['price']), float(b['size'])))
        for a in msg['asks']:
            asks.append((float(a['price']), float(a['size'])))
        self.ls_bids, self.ls_asks = bids, asks
