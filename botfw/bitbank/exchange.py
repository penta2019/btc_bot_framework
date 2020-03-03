from ..base.exchange import ExchangeBase
from .websocket import BitbankWebsocket
from .trade import BitbankTrade
from .orderbook import BitbankOrderbook
from .order import BitbankOrderManager, BitbankOrderGroupManager
from .api import BitbankApi


class Bitbank(ExchangeBase):
    Api = BitbankApi
    Websocket = BitbankWebsocket
    OrderManager = BitbankOrderManager
    OrderGroupManager = BitbankOrderGroupManager
    Trade = BitbankTrade
    Orderbook = BitbankOrderbook
