import logging
import json
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
        except websockets.ConnectionClosedOK:
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

        msg = json.loads(msg)
        exchange = msg['exchange']
        symbol = msg['symbol']
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
