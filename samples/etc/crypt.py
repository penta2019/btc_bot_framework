# cryptograpyはファイルの暗号化を行うためのライブラリです。

# 使い方

# 0.テスト用のjsonファイルを作成
#   $ echo '{"hello": "world!!"}' > plain.json

# 1.キーの生成して文字列を控える。(b''は不要)
# 注) cryptograpyはccxtインストール時に一緒にインストールされる。
#   $ python3
#   >>> from cryptography.fernet import Fernet
#   >>> Fernet.generate_key()
#   b'ランダムに生成されたキー'

# 2.jsonファイルを暗号化
#   $ python3 bin/encrypt.py < plain.json > encrypted_json
#   key>       (1.で生成したキーをコピペ。貼り付けた文字列が見えないのは仕様)

# 3.復号できるか確認
#   $ python3 bin/decrypt.py < encrypted_json
#   key>       (1.で生成したキーをコピペ)

# 4.暗号化されたjsonファイルの読み込み
import botfw
print(botfw.load_encrypted_json_file('encrypted_json'))
