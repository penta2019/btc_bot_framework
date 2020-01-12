from ..base.trade import TradeBase
from .websocket import BitflyerWebsocket
from .api import ccxt_bitflyer
from ..etc.util import unix_time_from_ISO8601Z


class BitflyerTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitflyerWebsocket()
        self.ws.add_after_open_callback(self.__after_open)

    def __after_open(self):
        market_id = ccxt_bitflyer().market_id(self.symbol)
        ch = f'lightning_executions_{market_id}'
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
            self._trigger_callback(ts, price, size)
