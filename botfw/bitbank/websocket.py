import traceback
import json

from ..base.websocket import WebsocketBase
from ..etc.util import run_forever_nonblocking

# engine.io-protocol
# 0 open
# 1 close
# 2 ping
# 3 pong
# 4 message

# socket.io-protocol (engine.io-protocol=4)
# 0 connect
# 1 disconnect
# 2 event
# 3 ack
# 4 error
# 5 binary_event
# 6 binary_ack


class BitbankWebsocket(WebsocketBase):
    ENDPOINT = 'wss://stream.bitbank.cc/socket.io/?EIO=3&transport=websocket'

    def __init__(self, key=None, secret=None):
        super().__init__(key, secret)
        run_forever_nonblocking(self.__ping_worker, self.log, 25)

    def _subscribe(self, ch):
        msg = f'42["join-room", "{ch}"]'
        self.send_raw(msg)
        self.log.info(msg)

    def _on_message(self, msg):
        ep = int(msg[0])  # engine.io-protocol
        sp = None  # socket.io-protocol

        if ep == 4:  # message
            sp = int(msg[1])
            content = msg[2:]
        else:
            content = msg[1:]

        try:
            if ep == 4 and sp == 2:
                m = json.loads(content)[1]
                ch = m['room_name']
                self._ch_cb[ch](m)
        except Exception:
            self.log.error(traceback.format_exc())

    def __ping_worker(self):
        if self.is_open:
            self.send_raw('2')  # ping
