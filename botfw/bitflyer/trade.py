from .websocket import *
from ..etc.util import *


class BitflyerTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitflyerWebsocket()
        self.ws.add_after_open_cb(self.__after_open)

    def __after_open(self):
        ch = f'lightning_executions_{self.symbol}'
        self.ws.subscribe(ch, self.__on_message)

    def __on_message(self, msg):
        for t in msg['params']['message']:
            ts = unix_time_from_ISO8601Z(t['exec_date'])
            price = int(t['price'])
            size = t['size']
            side = t['side']
            if side == 'SELL':
                size *= -1
            self.ltp = price
            self._trigger_cb(ts, price, size)
