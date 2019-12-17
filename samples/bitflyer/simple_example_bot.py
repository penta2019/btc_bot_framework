import time
import logging
import json
import traceback
import pprint

from botfw.bitflyer import *
from botfw.etc.util import setup_logger, run_forever_nonblocking

FX_BTC_JPY = 'FX_BTC_JPY'
BTC_JPY = 'BTC/JPY'

account = json.loads(open('account/bitflyer.json').read())
KEY = account['key']  # YOUR_API_KEY
SECRET = account['secret']  # YOUR_API_SECRET

setup_logger(logging.INFO)
log = logging.getLogger()

api = BitflyerApi({'apiKey': KEY, 'secret': SECRET})
ws = BitflyerWebsocket(KEY, SECRET)

fx_trade = BitflyerTrade(FX_BTC_JPY, ws)
fx_orderbook = BitflyerOrderbook(FX_BTC_JPY, ws)
# btc_trade = BitflyerTrade(BTC_JPY, ws)
# btc_orderbook = BitflyerOrderbook(BTC_JPY, ws)

om = BitflyerOrderManager(api, ws, retention=10)
ogm = BitflyerOrderGroupManager(
    om, trades={FX_BTC_JPY: fx_trade}, retention=10)
# ポジションズレを自動で修復。
# このオプションを利用する場合、外部のポジションは利用できません（自動で決済される）
# また、外部からの注文は定期的にすべてキャンセルされます。
ogm.set_position_sync_config(
    FX_BTC_JPY, lambda: api.get_total_position(FX_BTC_JPY), 0.01, 0.5)
fx_og = ogm.create_order_group(FX_BTC_JPY, 'fx')
fx_og.set_order_log(log)  # 自前で注文のログを表示する場合、ここは不要
# fx2_og = ogm.create_order_group(FX_BTC_JPY, 'fx2')
# btc_og = ogm.create_order_group(BTC_JPY, 'btc')


def fx_callback(ts, price, size):
    global fx_delay
    fx_delay = time.time() - ts


fx_delay = 0
fx_trade.add_callback(fx_callback)
while not fx_trade.ltp:
    print(f'initializing ltp...')
    time.sleep(1)


def main():
    buy_order = None
    sell_order = None

    while True:
        try:
            time.sleep(5)
            try:
                fx_best_bid = fx_orderbook.bids()[0]
                fx_best_ask = fx_orderbook.asks()[0]
            except Exception:
                print('initializing orderbook...')
                continue

            # print FX(ltp, bid, ask, delay)
            log.info(
                f'FX: {{ltp:{fx_trade.ltp}, '
                f'best_bid:{fx_best_bid[1]:.3f}@{fx_best_bid[0]}, '
                f'best_ask:{fx_best_ask[1]:.3f}@{fx_best_ask[0]}, '
                f'delay:{fx_delay:.3f}}}'
            )

            # print position info
            log.info(f'FX_POSITION: {fx_og.position_group}')

            # print API capacity and count
            log.info(f'API: {{capacity:{api.capacity}, count:{api.count}}}')

            # call rest api
            board_state = api.fetch_boardstate(FX_BTC_JPY)
            (f'BOARD_STATE: {board_state}')

            # pprint.pprint(om.orders)  # print all orders
            # pprint.pprint(fx_og.orders)  # print orders in 'fx' order group

            # BFFX ENDLESS LOSING MARKET MAKER LOGIC
            if board_state['state'] != 'RUNNING':
                continue

            # handle old order
            def handle_old_order(o):
                if o.state == OPEN:
                    fx_og.cancel_order(o)
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
            # fx_pos = fx_og.position_group.position
            # if not buy_order and fx_pos <= 0:
            #     price = fx_best_bid[0] - 500
            #     buy_order = fx_og.create_order(LIMIT, BUY, 0.01, price)
            # if not sell_order and fx_pos >= 0:
            #     price = fx_best_ask[0] + 500
            #     sell_order = fx_og.create_order(LIMIT, SELL, 0.01, price)

        except KeyboardInterrupt:
            break
        except Exception:
            log.error(traceback.format_exc())


# run_forever_nonblocking(main, log, 0) # for ipython
main()
