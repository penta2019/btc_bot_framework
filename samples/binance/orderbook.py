from botfw.base.orderbook import test_orderbook
from botfw.binance.orderbook import BinanceFutureOrderbook
test_orderbook(BinanceFutureOrderbook('BTC/USDT'))
