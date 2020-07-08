import logging
import traceback
import socket
import inspect
import pprint

from .util import run_forever_nonblocking


class CmdServer:
    def __init__(self, port):
        self.log = logging.getLogger(self.__class__.__name__)
        self.sock_addr = ('localhost', port)

        # {cmd:(func, log, response)}
        self.__commands = {'help': (self.help, True, True)}
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(self.sock_addr)

        self.log.info(f'open udp socket {self.sock_addr}')
        run_forever_nonblocking(self.__worker, self.log, 0)

    def register_command(self, func, log=True, response=True):
        if not callable(func):
            raise Exception(f'"{func}" is not callable')

        self.__commands[func.__name__] = (func, log, response)

    def help(self):
        '''Show command list'''
        details = []
        for name, (func, _log, _res) in self.__commands.items():
            # get cmd name and args
            spec = inspect.getargspec(func)
            args = ' '.join(spec.args[1:])
            if spec.varargs:
                args += ' args...'

            # format doc string
            if func.__doc__:
                lines = func.__doc__.split('\n')
                if lines and not lines[0].lstrip():
                    del lines[0]  # delete empty head line
                if lines and not lines[-1].lstrip():
                    del lines[-1]  # delete empty tail line
                lines = map(lambda l: '    ' + l.lstrip(), lines)
                doc = '\n'.join(lines)
            else:
                doc = '    no document'

            details.append(f'{name} {args}\n{doc}')
        return 'usage: Command args...\n\n' + '\n\n'.join(details) + '\n'

    def __worker(self):
        msg, addr = self.__sock.recvfrom(2 ** 16)
        msg = msg.decode().rstrip()
        args = msg.split()
        if not args:
            return

        log, response = True, True
        try:
            cmd = args[0]
            cmd_info = self.__commands.get(cmd)
            if cmd_info:
                func, log, response = cmd_info
                result = func(*args[1:])
            else:
                result = f'command "{cmd}" not found'
        except Exception:
            result = traceback.format_exc()

        if response:
            self.__sock.sendto(f'{result}\n'.encode(), addr)
        if log:
            self.log.info(f'recv {addr}: {msg} =>\n{result}')


class CmdClient:
    def __init__(self, port, print_result=True):
        self.log = logging.getLogger(self.__class__.__name__)
        self.server = ('localhost', port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.print_result = print_result
        run_forever_nonblocking(self.__worker, self.log, 0)

    def send(self, msg):
        self.sock.sendto(msg.encode(), self.server)

    def __worker(self):
        msg, _ = self.sock.recvfrom(8192)
        if self.print_result:
            print(msg.decode())


class Cmd:
    def __init__(self, globals_):
        self.globals = globals_

    def eval(self, *args):
        return eval(' '.join(args).replace(r'\s', ' '), self.globals)

    def exec(self, *args):
        return exec(' '.join(args).replace(r'\s', ' '), self.globals)

    def print(self, *args):
        return pprint.pformat(self.eval(*args))
