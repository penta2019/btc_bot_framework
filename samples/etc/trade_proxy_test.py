# trade_proxy.pyのテスト用のコード

# サーバのポート番号、取引所のクラス名、シンボル名を指定して実行
# $ python3 trade_proxy_test.py 51000 Bitflyer FX_BTC_JPY

import json
import sys

import asyncio
import websockets

port, exchange, symbol = sys.argv[1:]


async def run_app():
    async with websockets.connect(f'ws://127.0.0.1:{port}') as ws:
        await ws.send(json.dumps(
            {'exchange': exchange, 'symbol': symbol}))
        while True:
            print(await ws.recv())

try:
    asyncio.run(run_app())
except KeyboardInterrupt:
    pass
