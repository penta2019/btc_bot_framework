import json
from ..base.websocket import WebsocketBase


class BinanceWebsocketUserData(WebsocketBase):
    ENDPOINT = 'wss://stream.binance.com:9443/ws'

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
        self.url = f'{self.ENDPOINT}/{key}'

    def _on_open(self):
        super()._on_open()
        self._set_auth_result(True)

    def _on_message(self, msg):
        msg = json.loads(msg)
        self._run_callbacks(self.__cb, msg)


class BinanceFutureWebsocketUserData(BinanceWebsocketUserData):
    ENDPOINT = 'wss://fstream.binance.com/ws'
