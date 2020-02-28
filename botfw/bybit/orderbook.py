from ..base.orderbook import OrderbookBase
from .websocket import BybitWebsocket
from .api import BybitApi


class BybitOrderbook(OrderbookBase):
    CHANNEL = 'orderBookL2_25'

    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BybitWebsocket()

        market_id = BybitApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'{self.CHANNEL}.{market_id}', self.__on_message)

    def __on_message(self, msg):
        type_, data = msg['type'], msg['data']
        if type_ == 'snapshot':
            self.init()
            for d in data:
                self.__update(d)
        elif type_ == 'delta':
            for d in data['delete']:
                sd, key = self.__sd_and_key(d)
                del sd[key]
            for d in data['update']:
                self.__update(d)
            for d in data['insert']:
                self.__update(d)

        self._trigger_callback()

    def __update(self, d):
        sd, key = self.__sd_and_key(d)
        price, size = float(d['price']), d['size']
        sd[key] = [price, size / price]

    def __sd_and_key(self, data):
        if data['side'] == 'Sell':
            return self.sd_asks, data['id']
        else:
            return self.sd_bids, -data['id']
