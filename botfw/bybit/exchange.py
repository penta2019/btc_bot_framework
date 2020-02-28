from ..base.exchange import ExchangeBase
from .websocket import BybitWebsocket
from .trade import BybitTrade
from .orderbook import BybitOrderbook
from .order import BybitOrderManager, BybitOrderGroupManager
from .api import BybitApi


class Bybit(ExchangeBase):
    Api = BybitApi
    Websocket = BybitWebsocket
    OrderManager = BybitOrderManager
    OrderGroupManager = BybitOrderGroupManager
    Trade = BybitTrade
    Orderbook = BybitOrderbook
