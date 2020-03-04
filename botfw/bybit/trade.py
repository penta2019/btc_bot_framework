from ..base.trade import TradeBase
from .websocket import BybitWebsocket
from .api import BybitApi
from ..etc.util import unix_time_from_ISO8601Z


class BybitTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BybitWebsocket()

        market_id = BybitApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'trade.{market_id}', self.__on_message)

    def __on_message(self, msg):
        for t in msg['data']:
            ts = unix_time_from_ISO8601Z(t['timestamp'])
            price = t['price']
            size = t['size'] / price
            if t['side'] == 'Sell':
                size *= -1
            self.ltp = price
            self._trigger_callback(ts, price, size)
