import json
import traceback

from ..base.websocket import WebsocketBase


class GmocoinWebsocket(WebsocketBase):
    ENDPOINT = 'wss://api.coin.z.com/ws/public/v1'

    def __init__(self, key=None, secret=None):
        super().__init__(self.ENDPOINT)
        self.__request_table = {}  # (msg, cb, description)
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
        self.__ch_cb_map[(ch['channel'], ch['symbol'])] = cb

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            if 'error' in msg:
                self.log.error(msg['error'])
            else:
                self.__ch_cb_map[(msg['channel'], msg['symbol'])](msg)
        except Exception:
            self.log.error(traceback.format_exc())


# class GmoWeboscketPrivate(GmoWebsocket):
#     def __init__(self, api):
#         endpoint = 'wss://api.coin.z.com/ws/private/v1/' + token
#         super().__init__(endpoint)
