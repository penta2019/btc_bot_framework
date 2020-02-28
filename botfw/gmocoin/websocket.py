import json
import traceback

from ..base.websocket import WebsocketBase


class GmocoinWebsocket(WebsocketBase):
    ENDPOINT = 'wss://api.coin.z.com/ws/public/v1'
    NO_SYMBOL_CHANNEL = ['executionEvents']

    def __init__(self, key=None, secret=None):
        super().__init__(self.ENDPOINT)
        self.__request_table = {}  # (msg, cb)
        self.__ch_cb_map = {}

        if key and secret:
            self.log.warning('key and secret are ignored.')

    def command(self, op, params={}, cb=None):
        msg = params
        msg['command'] = op
        self.send(msg)
        self.log.info(f'{msg} => None')
        return None

    def subscribe(self, ch, cb):
        # ch = {'channel': channel, 'symbol': symbol}
        self.command('subscribe', ch)
        ch0 = ch['channel']
        ch1 = None if ch0 in self.NO_SYMBOL_CHANNEL else ch['symbol']
        self.__ch_cb_map[(ch0, ch1)] = cb

    def _on_open(self):
        self.__request_table = {}
        self.__ch_cb_map = {}
        super()._on_open()

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            if 'error' in msg:
                self.log.error(msg['error'])
            else:
                ch0 = msg['channel']
                ch1 = None if ch0 in self.NO_SYMBOL_CHANNEL else msg['symbol']
                self.__ch_cb_map[(ch0, ch1)](msg)
        except Exception:
            self.log.error(traceback.format_exc())


class GmocoinWebsocketPrivate(GmocoinWebsocket):
    ENDPOINT = 'wss://api.coin.z.com/ws/private/v1'

    def __init__(self, api):
        self.__api = api  # _on_init() may be called in super().__init__()
        super().__init__()

    def _on_init(self):
        res = self.__api.websocket_key()
        key = res['data']
        self.url = f'{self.ENDPOINT}/{key}'

    def _on_open(self):
        super()._on_open()
        self._set_auth_result(True)
