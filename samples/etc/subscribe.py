# 約定・板以外のチャンネルを購読する方法
# Websocketクラスは内部でコネクションを一つ生成します。
# subscribeは内部のコネクションが生成された後に呼び出す必要があるため、
# 以下のようにadd_after_open_callbackにsubscribeを行うコールバックを追加してください。
# このコールバックはコネクション切断による再接続の際にも自動で呼び出されます。

import botfw
ws = botfw.Bitflyer.Websocket()
ws.add_after_open_callback(
    lambda: ws.subscribe('lightning_ticker_BTC_JPY', print))
input()
