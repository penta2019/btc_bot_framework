from ..base.exchange import ExchangeBase
from .websocket import LiquidWebsocket
from .trade import LiquidTrade
from .orderbook import LiquidOrderbook
from .order import LiquidOrderManager, LiquidOrderGroupManager
from .api import LiquidApi


class Liquid(ExchangeBase):
    Api = LiquidApi
    Websocket = LiquidWebsocket
    OrderManager = LiquidOrderManager
    OrderGroupManager = LiquidOrderGroupManager
    Trade = LiquidTrade
    Orderbook = LiquidOrderbook
