import time
import logging
import json
import traceback

from botfw.base import *
from botfw.bitflyer.factory import BitflyerFactory as factory
# from botfw.bitmex.factory import BitmexFactory as factory
# from botfw.binance.factory import BinanceFactory as factory

from botfw.etc.util import setup_logger


SYMBOL = 'FX_BTC_JPY'  # FX_BTC_JPY(bitflyer)
# SYMBOL = 'BTC/USD'  # XBTUSD(bitmex)
# SYMBOL = 'BTC/USDT'  # BTCUSDT(binance future)

MIN_SIZE = 0.01  # 最小発注可能サイズ 0.01(bitflyer), 1(bitmex), 0.001(binance)

account = json.loads(open('account/key_secret.json').read())
ccxt_config = {
    'apiKey': account['key'],  # YOUR_API_KEY
    'secret': account['secret'],  # YOUR_API_SECRET
    # 'options': {'defaultType': 'future'},  # Binance future用
}

# ==================== ここから取引所共通のコード ====================
setup_logger(logging.INFO)
log = logging.getLogger()

f = factory()
f.create_basics(ccxt_config)
api = f.api
ws = f.websocket
om = f.order_manager
ogm = f.order_group_manager

# ポジション自動修復。
# ogm.set_position_sync_config(SYMBOL, MIN_SIZE, MIN_SIZE * 100)

trade = f.create_trade(SYMBOL)
orderbook = f.create_orderbook(SYMBOL)
og = f.create_order_group(SYMBOL, 'test1')
og.set_order_log(log)  # 自前で注文のログを表示する場合、ここは不要
# og.add_event_callback(lambda e: print(e.__dict__))　# 注文イベント取得時のコールバック関数


def trade_cb(ts, price, size):
    global delay
    delay = time.time() - ts


delay = 0
trade.add_callback(trade_cb)

# 最終取引価格を取得するまで待機
while not trade.ltp:
    print(f'initializing ltp...')
    time.sleep(1)


if __name__ == '__main__':
    buy_order = None
    sell_order = None

    while True:
        try:
            time.sleep(10)

            best_bid = orderbook.bids()[0]
            best_ask = orderbook.asks()[0]

            log.info(
                f'ltp:{trade.ltp}, '
                f'best_bid:{best_bid[1]:.3f}@{best_bid[0]}, '
                f'best_ask:{best_ask[1]:.3f}@{best_ask[0]}, '
                f'delay:{delay:.3f}'
            )
            log.info(f'position: {og.position_group}')
            log.info(f'api capacity: {api.capacity}')
            log.info(f'api count: {api.count}')

            # pprint.pprint(om.orders)  # すべての注文の表示
            # pprint.pprint(og.orders)  # OrderGroupに属する注文の表示

            if api.fetch_status()['status'] != 'ok':
                continue

            # handle old order
            def handle_old_order(o):
                if o.state == OPEN:
                    og.cancel_order(o)
                if o.state == WAIT_CANCEL:
                    time.sleep(1)
                if o.state in [CLOSED, CANCELED]:
                    return None
                return o

            if buy_order:
                buy_order = handle_old_order(buy_order)
            if sell_order:
                sell_order = handle_old_order(sell_order)

            # create order
            pos = og.position_group.position
            if not buy_order and pos <= 0:
                price = best_bid[0]
                buy_order = og.create_order(LIMIT, BUY, MIN_SIZE, price)
            if not sell_order and pos >= 0:
                price = best_ask[0]
                sell_order = og.create_order(LIMIT, SELL, MIN_SIZE, price)

        except KeyboardInterrupt:
            break
        except Exception:
            log.error(traceback.format_exc())
