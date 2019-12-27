from ..base.exchange import ExchangeBase
from .websocket import BinanceWebsocket, BinanceFutureWebsocket
from .trade import BinanceTrade, BinanceFutureTrade
from .orderbook import BinanceOrderbook, BinanceFutureOrderbook
from .order import (
    BinanceOrderManager, BinanceOrderGroupManager,
    BinanceFutureOrderManager, BinanceFutureOrderGroupManager)
from .api import BinanceApi, BinanceFutureApi


class Binance(ExchangeBase):
    Api = BinanceApi
    Websocket = BinanceWebsocket
    OrderManager = BinanceOrderManager
    OrderGroupManager = BinanceOrderGroupManager
    Trade = BinanceTrade
    Orderbook = BinanceOrderbook


class BinanceFuture(ExchangeBase):
    Api = BinanceFutureApi
    Websocket = BinanceFutureWebsocket
    OrderManager = BinanceFutureOrderManager
    OrderGroupManager = BinanceFutureOrderGroupManager
    Trade = BinanceFutureTrade
    Orderbook = BinanceFutureOrderbook
