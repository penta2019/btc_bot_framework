from ..base.websocket import WebsocketBase
from .jwt import create_jwt


class LiquidWebsocket(WebsocketBase):
    ENDPOINT = 'wss://tap.liquid.com/app/LiquidTapClient'

    def command(self, op, args=None, cb=None):
        msg = {'event': op}
        if args:
            msg['data'] = args

        self.send(msg)
        self.log.info(f'{msg}')

    def _subscribe(self, ch):
        self.command('pusher:subscribe', {'channel': ch})

    def _authenticate(self):
        auth_payload = {
            'path': '/realtime',
            'headers': {
                'X-Quoine-Auth': create_jwt(self.key, self.secret),
            },
        }
        self.command('quoine:auth_request', auth_payload)

    def _handle_message(self, msg):
        e = msg['event']
        if e in ['created', 'updated', 'pnl_updated']:
            self._ch_cb[msg['channel']](msg)
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
