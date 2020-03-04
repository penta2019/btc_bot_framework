from ..base.trade import TradeBase
from .websocket import BitflyerWebsocket
from .api import BitflyerApi
from ..etc.util import unix_time_from_ISO8601Z


class BitflyerTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitflyerWebsocket()

        market_id = BitflyerApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(
            f'lightning_executions_{market_id}', self.__on_message)

    def __on_message(self, msg):
        for t in msg['params']['message']:
            ts = unix_time_from_ISO8601Z(t['exec_date'])
            price = float(t['price'])
            size = t['size']
            if t['side'] == 'SELL':
                size *= -1
            self.ltp = price
            self._trigger_callback(ts, price, size)
