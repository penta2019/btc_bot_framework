from ..base.trade import TradeBase
from .websocket import BinanceWebsocket
from .api import ccxt_binance


class BinanceTrade(TradeBase):
    def __init__(self, symbol, ws=None, future=False):
        super().__init__()
        self.symbol = symbol
        self.ws = ws or BinanceWebsocket(future=future)
        self.ws.add_after_open_callback(self.__after_open)

    def __after_open(self):
        market_id = ccxt_binance.market_id(self.symbol)
        ch = f'{market_id.lower()}@trade'
        self.ws.subscribe(ch, self.__on_message)

    def __on_message(self, msg):
        ts = msg['E'] / 1000
        price = float(msg['p'])
        size = float(msg['q'])
        if msg['m']:
            size *= -1
        self.ltp = price

        self._trigger_callback(ts, price, size)
