from ..base.orderbook import OrderbookBase
from .websocket import BitmexWebsocket
from .api import ccxt_bitmex


class BitmexOrderbook(OrderbookBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitmexWebsocket()
        self.ws.add_after_open_callback(self.__after_open)

    def __after_open(self):
        self.init()
        market_id = ccxt_bitmex.market_id(self.symbol)
        ch = f'orderBookL2_25:{market_id}'
        self.ws.subscribe(ch, self.__on_message)

    def __on_message(self, msg):
        action, data = msg['action'], msg['data']
        if action in ['partial', 'insert']:
            for d in data:
                sd, key = self.__sd_and_key(d)
                price, size = d['price'], d['size']
                sd[key] = [price, size / price]
        elif action == 'update':
            for d in data:
                sd, key = self.__sd_and_key(d)
                e = sd[key]
                e[1] = d['size'] / e[0]
        elif action == 'delete':
            for d in data:
                sd, key = self.__sd_and_key(d)
                sd.pop(key, None)

        self._trigger_callback()

    def __sd_and_key(self, data):
        if data['side'] == 'Buy':
            return self.sd_bids, data['id']
        else:
            return self.sd_asks, -data['id']
