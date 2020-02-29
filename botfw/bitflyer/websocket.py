import time
import secrets

from ..base.websocket import WebsocketBase
from ..etc.util import hmac_sha256


class BitflyerWebsocket(WebsocketBase):
    ENDPOINT = 'wss://ws.lightstream.bitflyer.com/json-rpc'

    def command(self, op, args=None, cb=None):
        msg = {'method': op, 'id': self._request_id}
        if args:
            msg['params'] = args
        self._request_table[self._request_id] = (msg, cb)
        self._request_id += 1

        self.send(msg)

    def _subscribe(self, ch):
        self.command('subscribe', {'channel': ch})

    def _authenticate(self):
        now = int(time.time())
        nonce = secrets.token_hex(16)
        sign = hmac_sha256(self.secret, str(now) + nonce)
        self.command('auth', {
            'api_key': self.key,
            'timestamp': now,
            'nonce': nonce,
            'signature': sign},
            lambda msg: self._set_auth_result('result' in msg))

    def _handle_message(self, msg):
        if msg.get('method') == 'channelMessage':
            ch = msg['params']['channel']
            self._ch_cb[ch](msg)
        else:
            self.log.debug(f'recv: {msg}')
            if 'id' in msg:
                req, cb = self._request_table[msg['id']]
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
                self.log.warning(f'Unknown message: {msg}')
