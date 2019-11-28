from .websocket import *


class BitmexTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitmexWebsocket()
        self.ws.add_after_open_cb(self.__after_open)

    def __after_open(self):
        ch = f'trade:{self.symbol}'
        self.ws.subscribe(ch, self.__on_message, 'trade')

    def __on_message(self, msg):
        if msg['action'] == 'insert':
            ts = unix_time_from_ISO8601Z(msg['data'][0]['timestamp'])
            for t in msg['data']:
                price = t['price']
                size = round(t['size'] / price, 8)  # size in btc
                if t['side'] == 'Sell':
                    size *= -1
                self.ltp = price

                self._trigger_cb(ts, price, size)
