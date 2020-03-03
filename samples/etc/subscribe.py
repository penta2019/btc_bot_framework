# 約定・板以外のチャンネルの購読
# subscribe()の第二引数にチャンネルメッセージを処理するコールバック関数を渡してください。
# 切断時は自動的に再接続・チャンネル購読を行います。

import botfw
ws = botfw.Bitflyer.Websocket()
ws.subscribe('lightning_ticker_BTC_JPY', print)
input()
