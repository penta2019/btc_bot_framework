from ..base.orderbook import OrderbookBase
from .websocket import BybitWebsocket, BybitUsdtWebsocket
from .api import BybitApi


class BybitOrderbook(OrderbookBase):
    Websocket = BybitWebsocket
    CHANNEL = 'orderBookL2_25'

    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or self.Websocket()

        market_id = BybitApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'{self.CHANNEL}.{market_id}', self._on_message)

    def _on_message(self, msg):
        type_, data = msg['type'], msg['data']
        if type_ == 'snapshot':
            self.init()
            for d in data:
                self._update(d)
        elif type_ == 'delta':
            for d in data['delete']:
                sd, key = self._sd_and_key(d)
                del sd[key]
            for d in data['update']:
                self._update(d)
            for d in data['insert']:
                self._update(d)

        self._trigger_callback()

    def _update(self, data):
        sd, key = self._sd_and_key(data)
        price, size = float(data['price']), data['size']
        sd[key] = [price, size / price]

    def _sd_and_key(self, data):
        if data['side'] == 'Sell':
            return self.sd_asks, int(data['id'])
        else:
            return self.sd_bids, -int(data['id'])


class BybitUsdtOrderbook(BybitOrderbook):
    Websocket = BybitUsdtWebsocket

    def _on_message(self, msg):
        type_, data = msg['type'], msg['data']
        if type_ == 'snapshot':
            self.init()
            for d in data['order_book']:  # different from BybitOrderbook
                self._update(d)
        elif type_ == 'delta':
            for d in data['delete']:
                sd, key = self._sd_and_key(d)
                del sd[key]
            for d in data['update']:
                self._update(d)
            for d in data['insert']:
                self._update(d)

        self._trigger_callback()

    def _update(self, data):
        sd, key = self._sd_and_key(data)
        price, size = float(data['price']), data['size']
        sd[key] = [price, size]
