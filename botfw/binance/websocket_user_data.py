import json
from ..base.websocket import WebsocketBase


class BinanceWebsocketUserData(WebsocketBase):
    SPOT_ENDPOINT = 'wss://stream.binance.com:9443/ws'
    FUTURE_ENDPOINT = 'wss://fstream.binance.com/ws'

    def __init__(self, api):
        self.__api = api
        self.__cb = []
        super().__init__(None)

    def keep_alive(self):
        self.__api.listen_key('PUT')

    def add_callback(self, cb):
        self.__cb.append(cb)

    def _on_init(self):
        res = self.__api.listen_key()
        key = res['listenKey']
        if self.__api.future:
            self.url = f'{self.FUTURE_ENDPOINT}/{key}'
        else:
            self.url = f'{self.SPOT_ENDPOINT}/{key}'

    def _on_open(self):
        super()._on_open()
        self._set_auth_result(True)

    def _on_message(self, msg):
        msg = json.loads(msg)
        for cb in self.__cb:
            cb(msg)
