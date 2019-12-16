import json
import traceback

from ..base.websocket import WebsocketBase


class BinanceWebsocket(WebsocketBase):
    SPOT_ENDPOINT = 'wss://stream.binance.com:9443/ws'
    FUTURE_ENDPOINT = 'wss://fstream.binance.com/ws'

    def __init__(self, key=None, secret=None, future=False):
        endpoint = self.FUTURE_ENDPOINT if future else self.SPOT_ENDPOINT
        super().__init__(endpoint)
        self.__key = key
        self.__secret = secret
        self.__next_id = 1
        self.__request_table = {}
        self.__ch_cb_map = {}

        if self.__key and self.__secret:
            self.add_after_open_callback(
                lambda: self.authenticate(self.__key, self.__secret))

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

    def authenticate(self, key, secret):
        pass

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
