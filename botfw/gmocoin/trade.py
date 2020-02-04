from ..base.trade import TradeBase
from .websocket import GmocoinWebsocket
from .api import GmocoinApi
from ..etc.util import unix_time_from_ISO8601Z


class GmocoinTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or GmocoinWebsocket()
        self.ws.add_after_open_callback(self.__after_open)

    def __after_open(self):
        market_id = GmocoinApi.ccxt_instance().market_id(self.symbol)
        ch = {'channel': 'trades', 'symbol': market_id}
        self.ws.subscribe(ch, self.__on_message)

    def __on_message(self, msg):
        ts = unix_time_from_ISO8601Z(msg['timestamp'])
        price = float(msg['price'])
        size = float(msg['size'])
        if msg['side'] == 'SELL':
            size *= -1
        self.ltp = price
        self._trigger_callback(ts, price, size)
