import time
import json

from ..base.websocket import WebsocketBase
from ..etc.util import hmac_sha256


class BitmexWebsocket(WebsocketBase):
    ENDPOINT = 'wss://www.bitmex.com/realtime'

    def command(self, op, args=None, cb=None):
        msg = {'op': op}
        if args:
            msg['args'] = args
        self._request_table[json.dumps(msg)] = (msg, cb)
        self._request_id += 1

        self.send(msg)

    def _subscribe(self, ch):
        if ':' in ch:
            key = ch.split(':')[0]  # e.g. trade:XBTUSD -> trade
            if key in self._ch_cb and self._ch_cb[key] != self._ch_cb[ch]:
                raise Exception(f'channel "{key}" is already subscribed')
            self._ch_cb[key] = self._ch_cb[ch]

        self.command('subscribe', [ch])

    def _authenticate(self):
        expires = int(time.time() * 1000)
        sign = hmac_sha256(self.secret, f'GET/realtime{expires}')
        self.command(
            'authKeyExpires', [self.key, expires, sign],
            lambda msg: self._set_auth_result('success' in msg))

    def _handle_message(self, msg):
        table = msg.get('table')
        if table:
            self._ch_cb[table](msg)
        else:
            self.log.debug(f'revc: {msg}')
            if 'request' in msg:
                id_ = json.dumps(msg['request'])
                req, cb = self._request_table[id_]
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
