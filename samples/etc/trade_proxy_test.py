# trade_proxy.pyのテスト用のコード

# サーバのポート番号、取引所のクラス名、シンボル名を指定して実行
# $ python3 trade_proxy_test.py 51000 Bitflyer FX_BTC_JPY

import json
import sys

import websocket

port, exchange, symbol = sys.argv[1:]
ws = websocket.WebSocketApp(
    f'ws://127.0.0.1:{port}',
    on_open=lambda ws: ws.send(json.dumps(
        {'exchange': exchange, 'symbol': symbol})),
    on_message=lambda ws, msg: print(msg))
ws.run_forever()
