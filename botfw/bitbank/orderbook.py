from sortedcontainers import SortedDict

from ..base.orderbook import OrderbookBase
from .websocket import BitbankWebsocket
from .api import BitbankApi


class BitbankOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.ws = ws or BitbankWebsocket()
        self.symbol = symbol

        market_id = BitbankApi.ccxt_instance().market_id(symbol)
        self.ch_snapshot = f'depth_whole_{market_id}'
        self.ch_update = f'depth_diff_{market_id}'
        self.ws.subscribe(self.ch_snapshot, self.__on_message)
        self.ws.subscribe(self.ch_update, self.__on_message)

    def __on_message(self, msg):
        d = msg['message']['data']
        ch = msg['room_name']

        if ch == self.ch_snapshot:
            bids, asks = SortedDict(), SortedDict()
            self.__update(bids, d['bids'], -1)
            self.__update(asks, d['asks'], 1)
            self.sd_bids, self.sd_asks = bids, asks
        elif ch == self.ch_update:
            self.__update(self.sd_bids, d['b'], -1)
            self.__update(self.sd_asks, d['a'], 1)

        self._trigger_callback()

    def __update(self, sd, d, sign):
        for i in d:
            p, s = float(i[0]), float(i[1])
            if s == 0:
                sd.pop(p * sign, None)
            else:
                sd[p * sign] = [p, s]
