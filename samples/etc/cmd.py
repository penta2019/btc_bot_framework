import logging

from botfw.etc.cmd import Cmd
from botfw.etc.util import setup_logger

# botfw.etc.cmdは外部から操作や転送を行うためのモジュールです


def sum_str(*args):
    '''return sum of arguments'''
    return sum(map(int, args))  # 引数はすべて文字列であることに注意


def god(*args):
    return eval(' '.join(args).replace(r'\s', ' '), globals())


class Test:
    def __init__(self):
        self.data = []

    def add_data(self, *args):
        '''add args to self.data'''
        self.data.append(args)

    def show_data(self):
        '''return self.data'''
        return self.data


setup_logger(logging.INFO)

# 指定したport番号でlocalhostからのみアクセス可能なUDPのポートを開きます
cmd = Cmd(55555)  # '$ ss -upl' でポートが確かに開いてるか確認できます

# 外部から呼び出したい関数をCmdに追加
cmd.register_command(sum_str)
cmd.register_command(god)  # あらゆる処理を実行できる神コマンド。主にデバッグ用

# クラスメソッドを登録する場合
test_class = Test()
cmd.register_command(test_class.add_data)   # ログを表示したくない場合は log=False
cmd.register_command(test_class.show_data)  # 返信が必要ない場合は response=False


input()  # 終了しないように入力待ちで待機

# 動作テストにはnetcat(環境よってはnc)コマンドが便利
# $ netcat -u localhost 55555
# help
#     {略}
# sum_str 1 2 3 4
#     10
# add_data a b c
#     None
# add_data 1 2 3
#     None
# show_data
#     [('a', 'b', 'c'), ('1', '2', '3')]
# god cmd.__dict__
#     {略}
# god cmd.log.info('hello world')
#     None

# ipythonからCmdClientを利用する方法
# $ ipython
# : from botfw.etc.cmd import CmdClient
# : c = CmdClient(55555)
# : c.send("god cmd.log.info('hello world')")
