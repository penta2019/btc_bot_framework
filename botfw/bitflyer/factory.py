from ..base.factory import FactoryBase
from .websocket import BitflyerWebsocket
from .trade import BitflyerTrade
from .orderbook import BitflyerOrderbook
from .order import BitflyerOrderManager, BitflyerOrderGroupManager
from .api import BitflyerApi


class BitflyerFactory(FactoryBase):
    Api = BitflyerApi
    Websocket = BitflyerWebsocket
    OrderManager = BitflyerOrderManager
    OrderGroupManager = BitflyerOrderGroupManager
    Trade = BitflyerTrade
    Orderbook = BitflyerOrderbook
