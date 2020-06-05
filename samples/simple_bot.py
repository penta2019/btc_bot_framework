import time
import logging
import json
import traceback

import botfw as fw

# ==================== このセクションを書き換えてください ====================
account = json.loads(open('account/key_secret.json').read())  # ここはコメントアウト
ccxt_config = {
    'apiKey': account['key'],     # YOUR_API_KEY
    'secret': account['secret'],  # YOUR_API_SECRET
}

# FX_BTC_JPY @bitflyer
exchange = fw.Bitflyer
SYMBOL = 'FX_BTC_JPY'
MIN_SIZE = 0.01

# XBTUSD @bitmex
# exchange = fw.Bitmex
# SYMBOL = 'BTC/USD'
# MIN_SIZE = 1

# BTCUSDT @binance(future)
# exchange = fw.BinanceFuture
# SYMBOL = 'BTC/USDT'
# MIN_SIZE = 0.001

# BTC_JPY @liquid
# exchange = fw.Liquid
# SYMBOL = 'BTC/JPY'
# MIN_SIZE = 0.01

# BTCUSD @bybit
# exchange = fw.Bybit
# SYMBOL = 'BTC/USD'
# MIN_SIZE = 1

# bitbank, gmocoinの注文・建玉管理は現状未対応。

# ==================== ここから取引所共通のコード ====================
fw.setup_logger(logging.INFO)
log = logging.getLogger()

# simulate=Trueにすると実際には注文を出さずにリアルタイムシミュレーションを行う
# シミュレーションの場合はccxt_configの'apiKey'と'secret'はNoneでOK
ex = exchange(simulate=False)
ex.init_account(ccxt_config)
api = ex.api
ws = ex.websocket
om = ex.order_manager
ogm = ex.order_group_manager

# 手数料がアカウントごとに異なる取引所のシミュレーションを行う場合(bitflyerの'BTC/JPY'など)
# simulator = om.prepare_simulator('BTC/JPY')
# simulator.taker_fee = 0.0001
# simulator.maker_fee = 0.0001

# ポジション自動修復(bitflyer, binance, bitmexのみ)。 BF現物は非対応（手数料がポジションから引かれる為）
# ogm.set_position_sync_config(SYMBOL, MIN_SIZE, MIN_SIZE * 100)

trade = ex.create_trade(SYMBOL)
orderbook = ex.create_orderbook(SYMBOL)
og = ex.create_order_group(SYMBOL, 'test1')
og.set_order_log(log)  # create_order, cancel_orderのログを表示
# og.add_event_callback(lambda e: print(e.__dict__))  # 注文イベント取得時のコールバック関数

# 外部操作・デバッグ用のUDPコマンドラインインターフェース
cmd = fw.Cmd(globals())
cmd_server = fw.CmdServer(50000)
cmd_server.register_command(cmd.eval)
cmd_server.register_command(cmd.exec)
cmd_server.register_command(cmd.print, log=False)


# 約定データの遅延時間測定
def trade_cb(ts, price, size):
    global delay
    delay = time.time() - ts


delay = 0
trade.add_callback(trade_cb)

# tradeとorderbookが初期化される(最初のデータが届く)まで待機
trade.wait_initialized()
orderbook.wait_initialized()


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
            # pprint.pprint(og.get_orders())  # OrderGroupに属する注文の表示

            # サーバーが稼働中であることを確認
            if api.fetch_status()['status'] != 'ok':
                continue

            # 古い注文の処理
            def handle_old_order(o):
                if o.state == fw.OPEN:
                    og.cancel_order(o)
                if o.state == fw.WAIT_CANCEL:
                    time.sleep(1)
                if o.state in [fw.CLOSED, fw.CANCELED]:
                    return None
                return o

            if buy_order:
                buy_order = handle_old_order(buy_order)
            if sell_order:
                sell_order = handle_old_order(sell_order)

            # best bid, best askに最小ロットで指値
            pos = og.position_group.position
            if not buy_order and pos <= 0:
                price = best_bid[0]
                buy_order = og.create_order(
                    fw.LIMIT, fw.BUY, MIN_SIZE, price)
            if not sell_order and pos >= 0:
                price = best_ask[0]
                sell_order = og.create_order(
                    fw.LIMIT, fw.SELL, MIN_SIZE, price)

        except KeyboardInterrupt:
            break
        except Exception:
            log.error(traceback.format_exc())
