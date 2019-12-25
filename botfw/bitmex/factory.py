from ..base.factory import FactoryBase
from .websocket import BitmexWebsocket
from .trade import BitmexTrade
from .orderbook import BitmexOrderbook
from .order import BitmexOrderManager, BitmexOrderGroupManager
from .api import BitmexApi


class BitmexFactory(FactoryBase):
    Api = BitmexApi
    Websocket = BitmexWebsocket
    OrderManager = BitmexOrderManager
    OrderGroupManager = BitmexOrderGroupManager
    Trade = BitmexTrade
    Orderbook = BitmexOrderbook
