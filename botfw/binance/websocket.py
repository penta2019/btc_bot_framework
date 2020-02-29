from ..base.websocket import WebsocketBase


class BinanceWebsocket(WebsocketBase):
    ENDPOINT = 'wss://stream.binance.com:9443/ws'

    def command(self, op, args=None, cb=None):
        msg = {'method': op, 'id': self._request_id}
        if args:
            msg['params'] = args
        self._request_table[self._request_id] = (msg, cb)
        self._request_id += 1

        self.send(msg)

    def _subscribe(self, ch):
        key = ch.split('@')
        if len(key) < 2:
            raise Exception('Event type is not specified')
        symbol = key[0].upper()
        event = 'depthUpdate' if key[1] == 'depth' else key[1]
        self._ch_cb[(symbol, event)] = self._ch_cb[ch]

        self.command('SUBSCRIBE', [ch])

    def _authenticate(self):
        pass

    def _handle_message(self, msg):
        s = msg.get('s')
        e = msg.get('e')
        if e:
            self._ch_cb[(s, e)](msg)
        else:
            self.log.debug(f'recv: {msg}')
            if 'id' in msg:
                req, cb = self._request_table[msg['id']]
                if 'result' in msg:
                    res = msg['result']
                    self.log.info(f'{req} => {res}')
                elif 'error' in msg:  # TODO
                    err = msg['error']
                    code, message = err.get('code'), err.get('message')
                    self.log.error(f'{req} => {code}, {message}')

                if cb:
                    cb(msg)
            else:
                self.log.warning(f'Unknown message {msg}')


class BinanceFutureWebsocket(BinanceWebsocket):
    ENDPOINT = 'wss://fstream.binance.com/ws'


class BinanceWebsocketPrivate(WebsocketBase):
    ENDPOINT = 'wss://stream.binance.com:9443/ws'

    def __init__(self, api):
        self.__api = api  # _on_init() may be called in super().__init__()
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

    def _handle_message(self, msg):
        self._run_callbacks(self.__cb, msg)


class BinanceFutureWebsocketPrivate(BinanceWebsocketPrivate):
    ENDPOINT = 'wss://fstream.binance.com/ws'
