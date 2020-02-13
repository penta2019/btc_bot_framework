# trade_proxy.pyのテスト用のコード

# サーバのポート番号、取引所のクラス名、シンボル名を指定して実行
# $ python3 trade_proxy_test.py 51000 Bitflyer FX_BTC_JPY

import json
import sys

import websocket


def on_open(ws):
    ws.send(json.dumps(
        {'exchange': sys.argv[2], 'symbol': sys.argv[3]}))


if __name__ == '__main__':
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        f'ws://127.0.0.1:{sys.argv[1]}',
        on_open=on_open,
        on_message=lambda ws, msg: print(msg))
    ws.run_forever()
