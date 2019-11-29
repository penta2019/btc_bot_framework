from sortedcontainers import SortedDict

from ..base.orderbook import OrderbookBase
from .websocket import BitflyerWebsocket


class BitflyerOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ch_snapshot = f'lightning_board_snapshot_{self.symbol}'
        self.ch_update = f'lightning_board_{self.symbol}'
        self.ws = ws or BitflyerWebsocket()
        self.ws.add_after_open_cb(self.__after_open)

    def __after_open(self):
        self.init()
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

        self._trigger_cb()

    def __update(self, sd, d, sign):
        for i in d:
            p, s = int(i['price']), i['size']
            if s == 0:
                sd.pop(p * sign, None)
            else:
                sd[p * sign] = [p, s]
