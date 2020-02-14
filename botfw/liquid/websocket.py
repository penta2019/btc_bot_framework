import json
import traceback

from ..base.websocket import WebsocketBase
from .jwt import create_jwt


class LiquidWebsocket(WebsocketBase):
    ENDPOINT = 'wss://tap.liquid.com/app/LiquidTapClient'

    def __init__(self, key=None, secret=None):
        super().__init__(self.ENDPOINT)
        self.__key = key
        self.__secret = secret
        self.__ch_cb_map = {}

        if self.__key and self.__secret:
            self.add_after_open_callback(
                lambda: self.authenticate(self.__key, self.__secret))

    def command(self, op, args=[]):
        msg = {'event': op, 'data': args}
        self.send(msg)
        self.log.info(f'{msg}')

    def subscribe(self, ch, cb):
        self.command('pusher:subscribe', {'channel': ch})
        self.__ch_cb_map[ch] = cb

    def authenticate(self, key, secret):
        auth_payload = {
            'path': '/realtime',
            'headers': {
                'X-Quoine-Auth': create_jwt(key, secret),
            },
        }
        self.command('quoine:auth_request', auth_payload)

    def _on_open(self):
        self.__ch_cb_map = {}
        super()._on_open()

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            e = msg['event']
            if e == 'created':
                self.__ch_cb_map[msg['channel']](msg)
            elif e == 'updated':
                self.__ch_cb_map[msg['channel']](msg)
            elif e == 'pusher_internal:subscription_succeeded':
                ch = msg['channel']
                self.log.info(f'subscription succeeded: {ch}')
            elif e == 'quoine:auth_success':
                self._set_auth_result(True)
            elif e == 'quoine:auth_failure':
                self._set_auth_result(False)
            elif e == 'pusher:connection_established':
                pass
            else:
                self.log.warning(f'Unknown message: {msg}')
        except Exception:
            self.log.error(traceback.format_exc())
