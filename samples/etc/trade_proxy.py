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
import asyncio

import websockets

import botfw as fw


class TradeProxy:
    def __init__(self, port):
        self.log = logging.getLogger(self.__class__.__name__)
        self.clients = {}  # {client: ((exchange, symbol), callback)}
        self.trades = {}  # {(exchange, symbol)}
        self.server = websockets.serve(self.handle_ws, "localhost", port)
        self.loop = asyncio.get_event_loop()

    def run(self):
        self.loop.run_until_complete(self.server)
        self.loop.run_forever()

    async def handle_ws(self, ws, path):
        self.on_new_client(ws)
        try:
            while True:
                msg = await ws.recv()
                self.on_message_received(ws, msg)
        except websockets.ConnectionClosedOK as e:
            pass
        except Exception as e:
            self.log.error(e)
        self.on_client_left(ws)

    def on_new_client(self, ws):
        addr = ws.remote_address
        self.log.info(f'{addr}: OPEN')

        self.clients[addr] = ()

    def on_client_left(self, ws):
        addr = ws.remote_address
        self.log.info(f'{addr}: CLOSE')

        info = self.clients[addr]
        if info:
            key, cb = info
            t = self.trades[key]
            t.remove_callback(cb)
            if not t.cb:
                t.ws.stop()
                del self.trades[key]

        del self.clients[addr]

    def on_message_received(self, ws, msg):
        addr = ws.remote_address
        self.log.info(f'{addr}: "{msg}"')

        data = json.loads(msg)
        exchange = data['exchange']
        symbol = data['symbol']
        key = (exchange, symbol)

        if self.clients[addr]:
            self.log.error(f'{addr}: already subscribed channel')
            return

        t = self.trades.get(key)
        if not t:
            ex = getattr(fw, exchange)
            t = ex.Trade(symbol)
            self.trades[key] = t

        def cb(ts, price, size):
            asyncio.run_coroutine_threadsafe(
                ws.send(json.dumps([ts, price, size])), self.loop)

        t.add_callback(cb)
        self.clients[addr] = (key, cb)


if __name__ == '__main__':
    server_port, debug_port = sys.argv[1:]
    fw.setup_logger()

    # デバッグ用
    cmd = fw.Cmd(globals())
    cmd_server = fw.CmdServer(int(debug_port))
    cmd_server.register_command(cmd.eval)
    cmd_server.register_command(cmd.exec)
    cmd_server.register_command(cmd.print, log=False)

    proxy = TradeProxy(server_port)
    proxy.run()
