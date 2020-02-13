# import time
# import secrets
# import hmac
# import hashlib
import json
import traceback

from ..base.websocket import WebsocketBase


class LiquidWebsocket(WebsocketBase):
    ENDPOINT = 'wss://tap.liquid.com/app/LiquidTapClient'

    def __init__(self, key=None, secret=None):
        super().__init__(self.ENDPOINT)
        # self.__key = key
        # self.__secret = secret
        self.__request_table = {}  # (msg, cb)
        self.__ch_cb_map = {}

        # if self.__key and self.__secret:
        #     self.add_after_open_callback(
        #         lambda: self.authenticate(self.__key, self.__secret))

    def command(self, op, args=[], cb=None):
        msg = {'event': op, 'data': args}
        self.send(msg)
        self.__request_table[str(args)] = (msg, cb)
        return args

    def subscribe(self, ch, cb):
        self.command('pusher:subscribe', {'channel': ch})
        self.__ch_cb_map[ch] = cb

    def _on_open(self):
        self.__request_table = {}
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
                key = str({'channel': msg['channel']})
                req, cb = self.__request_table[key]
                res = msg['data']
                self.log.info(f'{req} => {res}')
                if cb:
                    cb(msg)
            elif e == 'pusher:connection_established':
                pass
            else:
                self.log.warning(f'Unknown message {msg}')
        except Exception:
            self.log.error(traceback.format_exc())
