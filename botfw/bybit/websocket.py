import time
import json
import hmac
import hashlib
import traceback

from ..base.websocket import WebsocketBase


class BybitWebsocket(WebsocketBase):
    ENDPOINT = 'wss://stream.bybit.com/realtime'

    def __init__(self, key=None, secret=None):
        self.__key = key
        self.__secret = secret
        self.__request_table = {}
        self.__ch_cb_map = {}
        super().__init__(self.ENDPOINT)

    def command(self, op, args=[], cb=None):
        msg = {'op': op, 'args': args}
        self.send(msg)
        key = json.dumps(msg)
        self.__request_table[key] = (msg, cb)
        return key

    def subscribe(self, ch, cb):
        self.command('subscribe', [ch])
        self.__ch_cb_map[ch] = cb

    def _on_init(self):
        if self.__key and self.__secret:
            expires = int(time.time() * 1000 + 1000)
            sign = hmac.new(
                self.__secret.encode(), f'GET/realtime{expires}'.encode(),
                hashlib.sha256).hexdigest()
            param = f'api_key={self.__key}&expires={expires}&signature={sign}'
            self.url = f'{self.ENDPOINT}?{param}'

    def _on_open(self):
        self.__next_id = 1
        self.__request_table = {}
        self.__ch_cb_map = {}
        super()._on_open()

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            topic = msg.get('topic')
            if topic:
                self.__ch_cb_map[topic](msg)
            else:
                self.log.debug(f'recv: {msg}')
                if 'request' in msg:
                    req, _ = self.__request_table[json.dumps(msg['request'])]
                    if 'success' in msg:
                        res = msg['success']
                        self.log.info(f'{req} => {res}')
                    elif 'error' in msg:
                        status, error = msg['status'], msg['error']
                        self.log.error(f'{req} => {status}, {error}')
                else:
                    self.log.warning(f'Unknown message: {msg}')
        except Exception:
            self.log.error(traceback.format_exc())
