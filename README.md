# 暗号通貨高頻度取引bot用websocketベースフレームワーク
## 概要
Pythonによる暗号通貨の高頻度取引bot向けフレームワークです。<br>
このフレームワークの役割は主に以下の３つです。
* websocketを最大限利用することでAPI制限とデータ取得遅延の問題を緩和すること。
* 取引所毎のwebsocketの仕様の差異を吸収すること。
* Bot開発において頻繁に出現する処理を再利用可能な形でモジュール化すること。

定数値(の内部値)はccxtとの一貫性や親和性のため取引所固有の値ではなく、ccxtに準拠しています。

* 'FX_BTC_JPY'(bitflyer) -> 'FX_BTC_JPY'(ccxt)
* 'BTC_JPY(bitflyer) -> 'BTC/JPY'(ccxt)
* 'BUY'(bitflyer), 'Buy'(bitmex), 'BUY'(binance) -> 'buy'(ccxt)
* 'LIMIT'(bitflyer), 'Limit'(bitmex), 'LIMIT'(binance) -> 'limit'(ccxt)

メイン通貨のみの簡単な動作確認しかできていないので、まだバグが多く残っているものと思われます。<br>
コードを参考にする程度に留めるか、実行する際はご自身で十分に検証を行ってください。<br>
プログラムの実行は自己責任です。不具合等によって損失が生じた場合でもこちらでは責任を負えません。<br>

## 主な機能
* websocket経由の約定データ、板情報、注文イベントの取得
* 注文・キャンセル (+bitflyer web注文)
* 注文イベントの処理: 注文の状態管理、ポジションサイズの計算、(未確定)損益計算
* ポジションの仮想的な分割（複数ロジックの実行）
* ポジションずれの自動補正
* 約定情報と板情報を使ったリアルタイムシミュレーション
* UDP経由の操作（webインターフェース等との連携用）
* クラス（ロジックファイル）の動的なロード・アンロード

## 対応状況
| 取引所      | API   | 約定情報 | 板情報 | 建玉管理・注文管理 | バグ取り |
|:-----------|:-----:|:-------:|:-----:|:---------------:|:------:|
| bitbank    | ○     | ○       | ○     | ×               | △      |    
| bitflyer   | ○     | ○       | ○     | ○               | ○      |    
| bitmex     | ○     | ○       | ○     | ○               | △      |
| binance    | ○     | ○       | ○     | ○               | △      |
| bybit      | △     | ○       | ○     | △               | △      |
| gmocoin    | ○     | ○       | ○     | ×               | △      |
| liquid     | ○     | ○       | ○     | △(JPYペアのみ)   | △      |

## このプロジェクトの対象外
* ローソク足やインジケータ等のチャート情報
* 実用的かつ具体的な売買ロジック

## 動作環境
* UNIX互換環境(Windowsは未検証)
* python>=3.6

## 依存ライブラリ
* ccxt>=1.20.44
* websocket-client>=0.48
* sortedcontainers
* python-socketio(オプション) – bitbank socketio
* beautifulsoup4 (オプション) – bitflyer web注文

## インストール
別のプロジェクトからモジュールを読み込みたい場合、方法２か方法３を利用してください。
### 方法1: そもそもインストールしない<br>
プロジェクト内に直接コードを書いて、プロジェクトルートからモジュールとして実行する場合は<br>
特にインストール作業は必要ありません。<br>
例えば、samples/bitflyer/orderbook.pyなら以下のように実行できます。(\_\_init\_\_.pyが必要かも)
```
$ python3 -m samples.bitflyer.orderbook
```

### 方法2: PYTHONPATHにプロジェクトディレクトリを追加<br>
使用しているシェルの設定ファイル(.bashrc, .zshrc等)にPYTHONPATHを追加します。<br>
正しい作法ですが、IDEによってはlinterのエラーがでたり、自動補完が効かなかったりします<br>
```
export PYTHONPATH="/path/to/btc_bot_framework:$PYTHONPATH"
```

### 方法3: パスの通った場所にシンボリックリンクを貼る(おすすめ)<br>
少し行儀の悪い方法ですが、一番トラブルの少ない方法です。たぶん。
1. パスの通っている場所を調べる。
```sh
$ python3 -c 'import sys; print(sys.path)'
['', '/usr/lib/python38.zip', '/usr/lib/python3.8', '/usr/lib/python3.8/lib-dynload',
 '/home/sk/.local/lib/python3.8/site-packages', '/usr/lib/python3.8/site-packages']
```
2. どこでも良いので（できれば管理者権限の必要ないディレクトリ）にbotfwのシンボリックリンクを作成。
```sh
$ cd /home/sk/.local/lib/python3.8/site-packages  # pip install --user で使われるディレクトリ
$ ln -s /path/to/btc_bot_framework/botfw botfw
```

## 使い方
**TODO**<br>
samples内のファイルを参照してください。
* samples/simple_bot.py 簡単なbotの実装例。あくまで使い方を確認する用。
* samples/bitlyfer/trade.py 約定データを取得して表示します。
* samples/bitflyer/orderbook.py 板情報を取得して表示します。
<br>
trade及びorderbookの利用方法はtest_trade()とtest_orderbook()を参照してください。それぞれ 'botfw/base/trade.py' と 'botfw/base/orderbook.py' 内にあります。

## 重要な変更点 (master)
commit 161 (9537ca0a8404e68d4021eac02c86d675492e0545) ----------

* 注文・キャンセルを非同期（デフォルト）に変更。同期はsync=Trueを引数に渡す。
* simulation mode 実装
* liquid 追加
* OrderGroupの注文一覧(orders)を削除。代わりにget_orders()を追加。
* 変数名commissionをfeeに変更。手数料周りの実装を共通化。

commit 217 (6667332febf181d03ad7f77f15600de9f82a6bb8) ----------


## 今後の予定
* GMOCoin 注文周りの実装

## お願い
一人で色々考えて作るのは結構大変なので、コミッターやデバッガー、改善案を出してくれる人を募集しています。<br>
OSSなので成果に対して報酬を出すことはできませんが、それでも良いという方は是非よろしくお願いします。
