from ..base.websocket import WebsocketBase


class GmocoinWebsocket(WebsocketBase):
    ENDPOINT = 'wss://api.coin.z.com/ws/public/v1'
    NO_SYMBOL_CHANNEL = ['executionEvents']

    def command(self, op, args=None, cb=None):
        msg = {'command': op}
        if args:
            msg.update(args)

        self.send(msg)
        self.log.info(f'{msg}')

    def _subscribe(self, ch):
        # ch = (channel, symbol)
        args = {'channel': ch[0]}
        if ch[1]:
            args['symbol'] = ch[1]
        self.command('subscribe', args)

    def _authenticate(self):
        pass

    def _handle_message(self, msg):
        if 'error' in msg:
            self.log.error(msg['error'])
        else:
            ch0 = msg['channel']
            ch1 = None if ch0 in self.NO_SYMBOL_CHANNEL else msg['symbol']
            self._ch_cb[(ch0, ch1)](msg)


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
