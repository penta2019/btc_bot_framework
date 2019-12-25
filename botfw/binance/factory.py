from ..base.factory import FactoryBase
from .websocket import BinanceWebsocket
from .trade import BinanceTrade
from .orderbook import BinanceOrderbook
from .order import BinanceOrderManager, BinanceOrderGroupManager
from .api import BinanceApi


class BinanceFactory(FactoryBase):
    Api = BinanceApi
    Websocket = BinanceWebsocket
    OrderManager = BinanceOrderManager
    OrderGroupManager = BinanceOrderGroupManager
    Trade = BinanceTrade
    Orderbook = BinanceOrderbook
