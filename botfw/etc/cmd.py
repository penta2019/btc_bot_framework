import logging
import traceback
import socket
import inspect

from .util import run_forever_nonblocking


class Cmd:
    def __init__(self, port):
        self.log = logging.getLogger(self.__class__.__name__)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', port))
        self.__commands = {'help': self.help}

        run_forever_nonblocking(self.__worker, self.log, 0)

    def register_class_methods_as_command(self, obj):
        for a in dir(obj):
            if a[0] == '_':
                continue  # skip __init__ or other private methods

            h = getattr(obj, a)
            if inspect.ismethod(h):
                if a in self.__commands:
                    self.log.error(
                        f'Command "{a}" already exists. Skipping')
                    continue
                self.__commands[a] = h

    def help(self):
        '''Show command list'''
        details = []
        for a, h in self.__commands.items():
            # get cmd name and args
            spec = inspect.getargspec(h)
            args = ' '.join(spec.args[1:])
            if spec.varargs:
                args += ' args...'

            # format doc string
            if h.__doc__:
                lines = h.__doc__.split('\n')
                if lines and not lines[0].lstrip():
                    del lines[0]  # delete empty head line
                if lines and not lines[-1].lstrip():
                    del lines[-1]  # delete empty tail line
                lines = map(lambda l: '    ' + l.lstrip(), lines)
                doc = '\n'.join(lines)
            else:
                doc = '    no document'

            details.append(f'{a} {args}\n{doc}')
        return 'usage: Command args...\n' + '\n'.join(details)

    def __worker(self):
        try:
            msg, addr = self.sock.recvfrom(2 ** 16)
            msg = msg.decode().rstrip()
            args = msg.split()
            if not args:
                return

            cmd = args[0]
            if cmd in self.__commands:
                res = self.__commands[cmd](*args[1:])
            else:
                res = f'command "{cmd}" not found'
        except socket.timeout:
            return
        except Exception:
            res = traceback.format_exc()

        self.log.info(f'recv {addr}: {msg} =>\n{res}')
        self.sock.sendto(f'{res}\n'.encode(), addr)
