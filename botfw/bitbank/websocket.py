import traceback
import logging

from ..base.websocket import WebsocketBase
from ..etc.util import StopRunForever


class BitbankWebsocket(WebsocketBase):
    ENDPOINT = 'wss://stream.bitbank.cc'

    def __init__(self, key=None, secret=None):
        super().__init__(key, secret)

        import socketio
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=1,
            reconnection_delay_max=30,
            logger=False)
        self.sio.logger.setLevel(logging.ERROR)
        self.sio.eio.logger.setLevel(logging.ERROR)
        self.sio.on('connect', self._on_open)
        self.sio.on('message', self._on_message)
        self.sio.on('disconnect', self._on_close)
        self.sio.on('error', self._on_error)
        self.sio.connect(self.ENDPOINT, transports=['websocket'])

    def _subscribe(self, ch):
        self.sio.emit('join-room', ch)
        self.log.info(f'join-room {ch}')

    def _on_init(self):
        # stop WebsocketBase.__worker()
        raise StopRunForever

    def _on_message(self, msg):
        try:
            ch = msg['room_name']
            self._ch_cb[ch](msg)
        except Exception:
            self.log.error(traceback.format_exc())
