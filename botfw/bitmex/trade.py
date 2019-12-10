from ..base.trade import TradeBase
from .websocket import BitmexWebsocket
from .api import ccxt_bitmex
from ..etc.util import unix_time_from_ISO8601Z


class BitmexTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitmexWebsocket()
        self.ws.add_after_open_callback(self.__after_open)

    def __after_open(self):
        market_id = ccxt_bitmex.market_id(self.symbol)
        ch = f'trade:{market_id}'
        self.ws.subscribe(ch, self.__on_message)

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
