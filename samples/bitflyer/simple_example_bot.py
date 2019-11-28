import time
import logging
import traceback
import pprint

import ccxt

from botfw.bitflyer import *

KEY = 'YOUR_API_KEY'
SECRET = 'YOUR_API_SECRET'

setup_logger(logging.INFO)
log = logging.getLogger()

ccxt = ccxt.bitflyer({'apiKey': KEY, 'secret': SECRET})
api = BitflyerApi(ccxt)
ws = BitflyerWebsocket(KEY, SECRET)

fx_trade = BitflyerTrade(FX_BTC_JPY, ws)
fx_orderbook = BitflyerOrderbook(FX_BTC_JPY, ws)
# btc_trade = BitflyerTrade(BTC_JPY, ws)
# btc_orderbook = BitflyerOrderbook(BTC_JPY, ws)

om = BitflyerOrderManager(api, ws, retention=10)
ogm = BitflyerOrderGroupManager(
    om, trades={FX_BTC_JPY: fx_trade}, retention=10)
fx_og = ogm.create_order_group('fx', FX_BTC_JPY)
# fx2_og = ogm.create_order_group('fx2', FX_BTC_JPY)
# btc_og = ogm.create_order_group('btc', BTC_JPY)


def fx_cb(ts, price, size):
    global fx_delay
    fx_delay = time.time() - ts


fx_delay = 0
fx_trade.add_cb(fx_cb)
while not fx_trade.ltp:
    print(f'initializing ltp...')
    time.sleep(1)

buy_order = None
sell_order = None

while True:
    try:
        time.sleep(5)
        try:
            fx_best_bid = fx_orderbook.bids()[0]
            fx_best_ask = fx_orderbook.asks()[0]
        except:
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
        log.info(f'API: {{capacity:{api.capacity}, count:{dict(api.count)}}}')

        # call rest api
        board_state = api.fetch_boardstate(FX_BTC_JPY)
        (f'BOARD_STATE: {board_state}')

        # pprint.pprint(om.orders)  # print all orders
        # pprint.pprint(fx_og.orders)  # print orders in 'fx' order group

        # ### BFFX ENDLESS LOSING MARKET MAKER LOGIC ###
        # if board_state['state'] != 'RUNNING':
        #     continue

        # # handle old order
        # def handle_old_order(o):
        #     if o.state == OPEN:
        #         fx_og.cancel_order(o)
        #         log.info(f'CANCEL: {o.child_order_acceptance_id}')
        #     if o.state == WAIT_CANCEL:
        #         time.sleep(1)
        #     if o.state in [CLOSED, CANCELED]:
        #         return None
        #     return o

        # if buy_order:
        #     buy_order = handle_old_order(buy_order)
        # if sell_order:
        #     sell_order = handle_old_order(sell_order)

        # # create order
        # fx_pos = fx_og.position_group.position
        # if not buy_order and fx_pos <= 0:
        #     price = fx_best_bid[0] - 500
        #     buy_order = fx_og.create_order(LIMIT, BUY, 0.01, price)
        #     id_ = buy_order.child_order_acceptance_id
        #     log.info(f'ORDER : {id_} FX_BTC_JPY LIMIT BUY 0.01 {price}')
        # if not sell_order and fx_pos >= 0:
        #     price = fx_best_ask[0] + 500
        #     sell_order = fx_og.create_order(LIMIT, SELL, 0.01, price)
        #     id_ = sell_order.child_order_acceptance_id
        #     log.info(f'ORDER : {id_} FX_BTC_JPY LIMIT SELL 0.01 {price}')

    except KeyboardInterrupt:
        break
    except:
        log.error(traceback.format_exc())
