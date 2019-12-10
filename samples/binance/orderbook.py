from botfw.base.orderbook import test_orderbook
from botfw.binance.orderbook import BinanceOrderbook
test_orderbook(BinanceOrderbook('BTC/USDT', future=True))
