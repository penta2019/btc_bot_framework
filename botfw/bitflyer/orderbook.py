from sortedcontainers import SortedDict

from ..base.orderbook import OrderbookBase
from .websocket import BitflyerWebsocket
from .api import BitflyerApi


class BitflyerOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.ws = ws or BitflyerWebsocket()
        self.symbol = symbol

        market_id = BitflyerApi.ccxt_instance().market_id(symbol)
        self.ch_snapshot = f'lightning_board_snapshot_{market_id}'
        self.ch_update = f'lightning_board_{market_id}'
        self.ws.subscribe(self.ch_snapshot, self.__on_message)
        self.ws.subscribe(self.ch_update, self.__on_message)

    def __on_message(self, msg):
        p = msg['params']
        ch = p['channel']
        m = p['message']
        if ch == self.ch_snapshot:
            bids, asks = SortedDict(), SortedDict()
            self.__update(bids, m['bids'], -1)
            self.__update(asks, m['asks'], 1)
            self.sd_bids, self.sd_asks = bids, asks
        elif ch == self.ch_update:
            self.__update(self.sd_bids, m['bids'], -1)
            self.__update(self.sd_asks, m['asks'], 1)

        self._trigger_callback()

    def __update(self, sd, d, sign):
        for i in d:
            p, s = float(i['price']), i['size']
            if s == 0:
                sd.pop(p * sign, None)
            else:
                sd[p * sign] = [p, s]
