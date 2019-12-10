import time
import logging
import json
import traceback
import pprint

from botfw.bitmex import *
from botfw.etc.util import setup_logger, run_forever_nonblocking

XBT_USD = 'BTC/USD'

account = json.loads(open('account/bitmex.json').read())
KEY = account['key']  # YOUR_API_KEY
SECRET = account['secret']  # YOUR_API_SECRET

setup_logger(logging.INFO)
log = logging.getLogger()

api = BitmexApi({'apiKey': KEY, 'secret': SECRET})
ws = BitmexWebsocket(KEY, SECRET)

trade = BitmexTrade(XBT_USD, ws)
orderbook = BitmexOrderbook(XBT_USD, ws)

om = BitmexOrderManager(api, ws, retention=10)
ogm = BitmexOrderGroupManager(om, trades={XBT_USD: trade}, retention=10)
og = ogm.create_order_group('test1', XBT_USD)


def callback(ts, price, size):
    global delay
    delay = time.time() - ts


delay = 0
trade.add_callback(callback)
while not trade.ltp:
    print(f'initializing ltp...')
    time.sleep(1)


def main():
    buy_order = None
    sell_order = None

    while True:
        try:
            time.sleep(5)
            try:
                best_bid = orderbook.bids()[0]
                best_ask = orderbook.asks()[0]
            except BaseException:
                print('initializing orderbook...')
                continue

            # print FX(ltp, bid, ask, delay)
            log.info(
                f'XBTUSD: {{ltp:{trade.ltp}, '
                f'best_bid:{best_bid[1]:.3f}@{best_bid[0]}, '
                f'best_ask:{best_ask[1]:.3f}@{best_ask[0]}, '
                f'delay:{delay:.3f}}}'
            )

            # print position info
            log.info(f'POSITION: {og.position_group}')

            # print API capacity and count
            log.info(
                f'API: {{capacity:{api.capacity}, count:{api.count}}}')

            # pprint.pprint(om.orders)  # print all orders
            # pprint.pprint(og.orders)  # print orders in 'fx' order group

            # handle old order
            def handle_old_order(o):
                if o.state in [CLOSED, CANCELED]:
                    return None
                return o

            if buy_order:
                buy_order = handle_old_order(buy_order)
            if sell_order:
                sell_order = handle_old_order(sell_order)

            # create order
            # pos = og.position_group.position
            # if not buy_order and pos <= 0:
            #     price = best_bid[0]
            #     buy_order = og.create_order(LIMIT, BUY, 1, price)
            #     id_ = buy_order.id
            #     log.info(f'ORDER : {id_} XBT_USD Limit Buy 1 {price}')
            # if not sell_order and pos >= 0:
            #     price = best_ask[0]
            #     sell_order = og.create_order(LIMIT, SELL, 1, price)
            #     id_ = sell_order.id
            #     log.info(f'ORDER : {id_} XBT_USD Limit Sell 1 {price}')

        except KeyboardInterrupt:
            break
        except BaseException:
            log.error(traceback.format_exc())


# run_forever_nonblocking(main, log, 0)
main()
