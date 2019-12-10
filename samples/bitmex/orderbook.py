from botfw.base.orderbook import test_orderbook
from botfw.bitmex.orderbook import BitmexOrderbook
test_orderbook(BitmexOrderbook('BTC/USD'))
