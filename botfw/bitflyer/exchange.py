from ..base.exchange import ExchangeBase
from .websocket import BitflyerWebsocket
from .trade import BitflyerTrade
from .orderbook import BitflyerOrderbook
from .order import BitflyerOrderManager, BitflyerOrderGroupManager
from .api import BitflyerApi


class Bitflyer(ExchangeBase):
    Api = BitflyerApi
    Websocket = BitflyerWebsocket
    OrderManager = BitflyerOrderManager
    OrderGroupManager = BitflyerOrderGroupManager
    Trade = BitflyerTrade
    Orderbook = BitflyerOrderbook
