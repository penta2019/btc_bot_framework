# TradeProxy
# 複数の約定情報websocketを束ねて一本化するためのwebsocketプロキシ
# 主にローカル環境でのデータ蓄積、分析、モニタリングなどで
# 複数のwebsocketを生成したくない（できない）場合を想定しています。
# 処理遅延が発生するので本番環境ではおすすめしません。

# websocketサーバのポート指定して実行
# $ python3 samples/etc/trade_proxy.py 51000

# クライアント側のon_openで購読したいチャンネルの情報を送信
# ws.send('{"exchange": "Bitflyer", "symbol": "FX_BTC_JPY"}')
# 複数チャンネルには対応していないのでチャンネルごとにwebsocketを生成してください。

import sys
import botfw as fw

try:
    fw.setup_logger()
    proxy = fw.TradeProxy(sys.argv[1])
    proxy.run()
except KeyboardInterrupt:
    pass
