from ..base.exchange import ExchangeBase
from .websocket import BybitWebsocket, BybitUsdtWebsocket
from .trade import BybitTrade, BybitUsdtTrade
from .orderbook import BybitOrderbook, BybitUsdtOrderbook
from .order import BybitOrderManager, BybitOrderGroupManager
from .api import BybitApi


class Bybit(ExchangeBase):
    Api = BybitApi
    Websocket = BybitWebsocket
    OrderManager = BybitOrderManager
    OrderGroupManager = BybitOrderGroupManager
    Trade = BybitTrade
    Orderbook = BybitOrderbook


class BybitUsdt(ExchangeBase):
    Api = BybitApi
    Websocket = BybitUsdtWebsocket
    OrderManager = None
    OrderGroupManager = None
    Trade = BybitUsdtTrade
    Orderbook = BybitUsdtOrderbook
