from ..base.exchange import ExchangeBase
from .websocket import BybitWebsocket, BybitUsdtWebsocket
from .trade import BybitTrade, BybitUsdtTrade
from .orderbook import BybitOrderbook, BybitUsdtOrderbook
from .order import (
    BybitOrderManager, BybitOrderGroupManager,
    # BybitUsdtOrderManager, BybitUsdtOrderGroupManager
)
from .api import BybitApi, BybitUsdtApi


class Bybit(ExchangeBase):
    Api = BybitApi
    Websocket = BybitWebsocket
    OrderManager = BybitOrderManager
    OrderGroupManager = BybitOrderGroupManager
    Trade = BybitTrade
    Orderbook = BybitOrderbook


class BybitUsdt(ExchangeBase):
    Api = BybitUsdtApi
    Websocket = BybitUsdtWebsocket
    OrderManager = None  # BybitUsdtOrderManager
    OrderGroupManager = None  # BybitUsdtOrderGroupManager
    Trade = BybitUsdtTrade
    Orderbook = BybitUsdtOrderbook
