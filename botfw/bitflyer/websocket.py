import time
import json
import secrets
import hmac
import hashlib
import traceback

from ..base.websocket import WebsocketBase


class BitflyerWebsocket(WebsocketBase):
    def __init__(self, key=None, secret=None):
        super().__init__('wss://ws.lightstream.bitflyer.com/json-rpc',
                         bool(key and secret))
        self.__key = key
        self.__secret = secret
        self.__auth_id = None
        self.__next_id = 1
        self.__request_table = {}

    def command(self, op, args=[], description=None):
        id_ = self.__next_id
        self.__next_id += 1
        msg = {'method': op, 'params': args, 'id': id_}
        self.send(msg)

        self.__request_table[id_] = description or msg
        return id_

    def _authenticate(self):
        now = int(time.time())
        nonce = secrets.token_hex(16)
        sign = hmac.new(self.__secret.encode(), (str(now) + nonce).encode(),
                        hashlib.sha256).hexdigest()
        id_ = self.command('auth', {
            'api_key': self.__key,
            'timestamp': now,
            'nonce': nonce,
            'signature': sign
        })
        self.__auth_id = id_

    def _subscribe(self, ch):
        self.command('subscribe', {'channel': ch})

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            ch = None
            if msg.get('method') == 'channelMessage':
                ch = msg['params']['channel']
                self._handle_ch_message(ch, msg)
            else:
                self.log.debug(f'recv: {msg}')
                id_ = msg.get('id')
                if id_:
                    req = self.__request_table[id_]
                    if 'result' in msg:
                        res = msg.get('result')
                        self.log.info(f'{req} => {res}')

                        if id_ == self.__auth_id:
                            self.is_auth = True
                    elif 'error' in msg:
                        err = msg['error']
                        code, message = err.get('code'), err.get('message')
                        self.log.error(f'{req} => {code}, {message}')

                        if id_ == self.__auth_id:
                            self.is_auth = False

        except Exception:
            self.log.debug(traceback.format_exc())
