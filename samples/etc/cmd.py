import logging

import botfw

# botfw.etc.cmdは外部から操作や転送を行うためのモジュールです


def sum_str(*args):
    '''return sum of arguments'''
    return sum(map(int, args))  # 引数はすべて文字列であることに注意


class Test:
    def __init__(self):
        self.data = []

    def add_data(self, *args):
        '''add args to self.data'''
        self.data.append(args)

    def show_data(self):
        '''return self.data'''
        return self.data


botfw.setup_logger(logging.INFO)

# 指定したport番号でlocalhostからのみアクセス可能なUDPのポートを開きます
cmd_server = botfw.CmdServer(55555)  # '$ ss -upl' でポートが確かに開いてるか確認できます

# 外部から呼び出したい関数をCmdに追加
cmd_server.register_command(sum_str)

# クラスメソッドを登録する場合
test = Test()
cmd_server.register_command(test.add_data)   # ログを表示したくない場合は log=False
cmd_server.register_command(test.show_data)  # 返信が必要ない場合は response=False

# 定義済みコマンド
cmd = botfw.Cmd(globals())
cmd_server.register_command(cmd.eval)  # あらゆる処理を実行できるコマンド。主にデバッグ用
cmd_server.register_command(cmd.exec)  # 同上。返り値がNoneになる代わりに代入や複数文の実行が可能
cmd_server.register_command(cmd.print, log=False)  # eval同様。返り値をpprintでフォーマットする

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
# eval cmd_server.__dict__
#     {略}
# eval cmd_server.log.info('hello world')
#     None

# インタラクティブモードからCmdClientを利用する方法
# $ python3
# >>> import botfw
# >>> c = botfw.CmdClient(55555)
# >>> c.send("eval cmd_server.log.info('hello world')")
