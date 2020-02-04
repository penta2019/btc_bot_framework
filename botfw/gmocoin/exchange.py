from ..base.exchange import ExchangeBase
from .websocket import GmocoinWebsocket
from .trade import GmocoinTrade
from .orderbook import GmocoinOrderbook
# from .order import GmocoinOrderManager, GmocoinOrderGroupManager
from .api import GmocoinApi


class Gmocoin(ExchangeBase):
    Api = GmocoinApi
    Websocket = GmocoinWebsocket
    # OrderManager = GmocoinOrderManager
    # OrderGroupManager = GmocoinOrderGroupManager
    Trade = GmocoinTrade
    Orderbook = GmocoinOrderbook
