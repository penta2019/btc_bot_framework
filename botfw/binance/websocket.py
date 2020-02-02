import json
import traceback

from ..base.websocket import WebsocketBase


class BinanceWebsocket(WebsocketBase):
    ENDPOINT = 'wss://stream.binance.com:9443/ws'

    def __init__(self, key=None, secret=None):
        super().__init__(self.ENDPOINT)
        self.__next_id = 1
        self.__request_table = {}
        self.__ch_cb_map = {}

        if key and secret:
            self.log.warning('key and secret are ignored.')

    def command(self, op, args=[], description=None):
        id_ = self.__next_id
        self.__next_id += 1
        msg = {'method': op, 'params': args, 'id': id_}
        self.send(msg)
        self.__request_table[id_] = description or msg
        return id_

    def subscribe(self, ch, cb):
        key = ch.split('@')
        if len(key) < 2:
            raise Exception('Event type is not specified')
        self.command('SUBSCRIBE', [ch])

        symbol = key[0].upper()
        event = 'depthUpdate' if key[1] == 'depth' else key[1]
        key = (symbol, event)
        self.__ch_cb_map[(key[0].upper(), key[1])] = cb
        return key

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            s = msg.get('s')
            e = msg.get('e')
            if e:
                self.__ch_cb_map[(s, e)](msg)
            else:
                self.log.debug(f'recv: {msg}')
                if 'id' in msg:
                    req = self.__request_table[msg['id']]
                    if 'result' in msg:
                        res = msg['result']
                        self.log.info(f'{req} => {res}')
                    elif 'error' in msg:  # TODO
                        err = msg['error']
                        code, message = err.get('code'), err.get('message')
                        self.log.error(f'{req} => {code}, {message}')
                else:
                    self.log.warning(f'Unknown message {msg}')
        except Exception:
            self.log.error(traceback.format_exc())


class BinanceFutureWebsocket(BinanceWebsocket):
    ENDPOINT = 'wss://fstream.binance.com/ws'


class BinanceWebsocketPrivate(WebsocketBase):
    ENDPOINT = 'wss://stream.binance.com:9443/ws'

    def __init__(self, api):
        self.__api = api
        self.__cb = []
        super().__init__(None)

    def keep_alive(self):
        self.__api.websocket_key('PUT')

    def add_callback(self, cb):
        self.__cb.append(cb)

    def _on_init(self):
        res = self.__api.websocket_key()
        key = res['listenKey']
        self.url = f'{self.ENDPOINT}/{key}'

    def _on_open(self):
        super()._on_open()
        self._set_auth_result(True)

    def _on_message(self, msg):
        msg = json.loads(msg)
        self._run_callbacks(self.__cb, msg)


class BinanceFutureWebsocketPrivate(BinanceWebsocketPrivate):
    ENDPOINT = 'wss://fstream.binance.com/ws'
