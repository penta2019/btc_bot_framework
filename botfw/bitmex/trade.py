from ..base.trade import TradeBase
from .websocket import BitmexWebsocket
from .api import BitmexApi
from ..etc.util import unix_time_from_ISO8601Z


class BitmexTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitmexWebsocket()

        market_id = BitmexApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'trade:{market_id}', self.__on_message)

    def __on_message(self, msg):
        if msg['action'] == 'insert':
            ts = unix_time_from_ISO8601Z(msg['data'][0]['timestamp'])
            for t in msg['data']:
                price = t['price']
                size = round(t['size'] / price, 8)  # size in btc
                if t['side'] == 'Sell':
                    size *= -1
                self.ltp = price
                self._trigger_callback(ts, price, size)
