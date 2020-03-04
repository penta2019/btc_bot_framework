from ..base.trade import TradeBase
from .websocket import BitbankWebsocket
from .api import BitbankApi


class BitbankTrade(TradeBase):
    def __init__(self, symbol, ws=None):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BitbankWebsocket()

        market_id = BitbankApi.ccxt_instance().market_id(self.symbol)
        self.ws.subscribe(f'transactions_{market_id}', self.__on_message)

    def __on_message(self, msg):
        for t in msg['message']['data']['transactions']:
            ts = t['executed_at'] / 1000
            price = float(t['price'])
            size = float(t['amount'])
            if t['side'] == 'sell':
                size *= -1
            self.ltp = price
            self._trigger_callback(ts, price, size)
