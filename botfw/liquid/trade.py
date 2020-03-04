import json

from ..base.trade import TradeBase
from .websocket import LiquidWebsocket


class LiquidTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or LiquidWebsocket()

        market_id = self.symbol.replace('/', '').lower()
        self.ws.subscribe(
            f'execution_details_cash_{market_id}', self.__on_message)

    def __on_message(self, msg):
        data = json.loads(msg['data'])
        ts = data['created_at']
        price = data['price']
        size = float(data['quantity'])
        if data['taker_side'] == 'sell':
            size *= -1
        self.ltp = price
        self._trigger_callback(ts, price, size)
