import time
import json

from ..base.websocket import WebsocketBase
from ..etc.util import hmac_sha256


class BybitWebsocket(WebsocketBase):
    ENDPOINT = 'wss://stream.bybit.com/realtime'

    def command(self, op, args=None, cb=None):
        msg = {'op': op}
        if args:
            msg['args'] = args
        self._request_table[json.dumps(msg)] = (msg, cb)

        self.send(msg)

    def _on_init(self):
        if self.key and self.secret:
            expires = int(time.time() * 1000 + 1000)
            sign = hmac_sha256(self.secret, f'GET/realtime{expires}')
            param = f'api_key={self.key}&expires={expires}&signature={sign}'
            self.url = f'{self.ENDPOINT}?{param}'

    def _on_open(self):
        super()._on_open()
        if self.key and self.secret:
            self._set_auth_result(True)

    def _subscribe(self, ch):
        self.command('subscribe', [ch])

    def _authenticate(self):
        pass

    def _handle_message(self, msg):
        topic = msg.get('topic')
        if topic:
            self._ch_cb[topic](msg)
        else:
            self.log.debug(f'recv: {msg}')
            if 'request' in msg:
                req, _ = self._request_table[json.dumps(msg['request'])]
                if 'success' in msg:
                    res = msg['success']
                    self.log.info(f'{req} => {res}')
                elif 'error' in msg:
                    status, error = msg['status'], msg['error']
                    self.log.error(f'{req} => {status}, {error}')
            else:
                self.log.warning(f'Unknown message: {msg}')
