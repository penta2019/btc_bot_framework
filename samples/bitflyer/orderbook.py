from botfw.base.orderbook import test_orderbook
from botfw.bitflyer.orderbook import BitflyerOrderbook
test_orderbook(BitflyerOrderbook('FX_BTC_JPY'))
