import time
import json
import secrets
import hmac
import hashlib
import traceback

from ..base.websocket import WebsocketBase


class BitflyerWebsocket(WebsocketBase):
    def __init__(self, key=None, secret=None):
        super().__init__('wss://ws.lightstream.bitflyer.com/json-rpc')
        self.__key = key
        self.__secret = secret
        self.__next_id = 1
        self.__request_table = {}  # (msg, cb, description)
        self.__ch_cb_map = {}

        if self.__key and self.__secret:
            self.add_after_open_callback(
                lambda: self.authenticate(self.__key, self.__secret))

    def command(self, op, args=[], cb=None, description=None):
        id_ = self.__next_id
        self.__next_id += 1
        msg = {'method': op, 'params': args, 'id': id_}
        self.send(msg)
        self.__request_table[id_] = (msg, cb, description)
        return id_

    def subscribe(self, ch, cb):
        self.command('subscribe', {'channel': ch})
        self.__ch_cb_map[ch] = cb

    def authenticate(self, key, secret):
        now = int(time.time())
        nonce = secrets.token_hex(16)
        sign = hmac.new(self.__secret.encode(), (str(now) + nonce).encode(),
                        hashlib.sha256).hexdigest()
        self.command('auth', {
            'api_key': self.__key,
            'timestamp': now,
            'nonce': nonce,
            'signature': sign
        }, lambda msg: self._set_auth_result('result' in msg))

    def _on_open(self):
        self.__next_id = 1
        self.__request_table = {}
        self.__ch_cb_map = {}
        super()._on_open()

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            if msg.get('method') == 'channelMessage':
                ch = msg['params']['channel']
                self.__ch_cb_map[ch](msg)
            else:
                self.log.debug(f'recv: {msg}')
                if 'id' in msg:
                    smsg, cb, desc = self.__request_table[msg['id']]
                    req = desc or smsg
                    if 'result' in msg:
                        res = msg['result']
                        self.log.info(f'{req} => {res}')
                    elif 'error' in msg:
                        err = msg['error']
                        code, message = err.get('code'), err.get('message')
                        self.log.error(f'{req} => {code}, {message}')

                    if cb:
                        cb(msg)
                else:
                    self.log.warn(f'Unknown message {msg}')
        except Exception:
            self.log.debug(traceback.format_exc())
