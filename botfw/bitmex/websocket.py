import time
import json
import traceback
import hmac
import hashlib

from ..base.websocket import WebsocketBase


class BitmexWebsocket(WebsocketBase):
    def __init__(self, key=None, secret=None):
        super().__init__('wss://www.bitmex.com/realtime')
        self.__key = key
        self.__secret = secret
        self.__request_table = {}  # (msg, cb, description)
        self.__ch_cb_map = {}

        if self.__key and self.__secret:
            self.add_after_open_callback(
                lambda: self.authenticate(self.__key, self.__secret))

    def command(self, op, args=[], cb=None, description=None):
        msg = {"op": op, "args": args}
        self.send(msg)
        id_ = json.dumps(msg)
        self.__request_table[id_] = (msg, cb, description)
        return id_

    def subscribe(self, ch, cb):
        key = ch.split(':')[0]
        if key in self.__ch_cb_map:
            raise Exception(f'channel "{key}" is already subscribed')

        self.command('subscribe', [ch])
        self.__ch_cb_map[key] = cb

    def authenticate(self, key, secret):
        expires = int(time.time() * 1000)
        sign = hmac.new(
            self.__secret.encode(), f'GET/realtime{expires}'.encode(),
            hashlib.sha256).hexdigest()
        self.command(
            'authKeyExpires', [self.__key, expires, sign],
            lambda msg: self._set_auth_result('success' in msg))

    def _on_open(self):
        self.__request_table = {}
        self.__ch_cb_map = {}
        super()._on_open()

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            table = msg.get('table')
            if table:
                self.__ch_cb_map[table](msg)
            else:
                self.log.debug(f'revc: {msg}')
                if 'request' in msg:
                    id_ = json.dumps(msg['request'])
                    smsg, cb, desc = self.__request_table[id_]
                    req = desc or smsg
                    if 'success' in msg:
                        res = msg['success']
                        self.log.info(f'{req} => {res}')
                    elif 'error' in msg:
                        status, error = msg['status'], msg['error']
                        self.log.error(f'{req} => {status}, {error}')

                    if cb:
                        cb(msg)
                else:
                    self.log.warning(f'Unknown message: {msg}')
        except Exception:
            self.log.error(traceback.format_exc())
