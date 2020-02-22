# 複数の約定情報websocketを束ねて一本化するためのwebsocketプロキシ
# 主にローカル環境でのデータ蓄積、分析、モニタリングなどで
# 複数のwebsocketを生成したくない（できない）場合を想定しています。
# 処理遅延が発生するので本番環境ではおすすめしません。

# websocketサーバのポートとデバッグ用のポートを指定して実行
# $ python3 trade_proxy.py 51000 51001

# クライアント側のon_openで購読したいチャンネルの情報を送信
# ws.send('{"exchange": "Bitflyer", "symbol": "FX_BTC_JPY"}')
# 複数チャンネルには対応していないのでチャンネルごとにwebsocketを生成してください。

import logging
import json
import sys

from websocket_server import WebsocketServer

import botfw as fw

server_port, debug_port = sys.argv[1:]

log = logging.getLogger()
fw.setup_logger()

# デバッグ用
cmd = fw.Cmd(globals())
cmd_server = fw.CmdServer(int(debug_port))
cmd_server.register_command(cmd.eval)
cmd_server.register_command(cmd.exec)
cmd_server.register_command(cmd.print, log=False)

clients = {}  # {client: ((exchange, symbol), callback)}
trades = {}  # {(exchange, symbol)}


def on_new_client(client, server):
    addr = client['address']
    log.info(f'{addr}: OPEN')

    clients[addr] = ()


def on_client_left(client, server):
    addr = client['address']
    log.info(f'{addr}: CLOSE')

    info = clients[addr]
    if info:
        key, cb = info
        t = trades[key]
        t.remove_callback(cb)
        if not t.cb:
            t.ws.stop()
            del trades[key]

    del clients[addr]


def on_message_received(client, server, message):
    addr = client['address']
    log.info(f'{addr}: "{message}"')

    data = json.loads(message)
    exchange = data['exchange']
    symbol = data['symbol']
    key = (exchange, symbol)

    if clients[addr]:
        log.error(f'{addr}: already subscribed channel')
        return

    t = trades.get(key)
    if not t:
        ex = getattr(fw, exchange)
        t = ex.Trade(symbol)
        trades[key] = t

    def cb(ts, price, size):
        server.send_message(client, json.dumps([ts, price, size]))

    t.add_callback(cb)
    clients[addr] = (key, cb)


if __name__ == "__main__":
    server = WebsocketServer(port=int(server_port), host='127.0.0.1')
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message_received)
    server.run_forever()
