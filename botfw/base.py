import time
import logging
import traceback
import json

import secrets
import hmac
import hashlib

import websocket
from sortedcontainers import SortedDict

from .etc.util import *


def test_trade(t, trace=False, log_level=logging.DEBUG):
    setup_logger(log_level)
    if trace:
        websocket.enableTrace(True)
    try:
        t.add_cb(lambda ts, p, s: print(f'{ts:.3f} {p:.1f} {s:+.3f}'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def test_orderbook(ob, trace=False, log_level=logging.DEBUG):
    setup_logger(log_level)
    if trace:
        websocket.enableTrace(True)
    time.sleep(1)
    try:
        while True:
            for p, s in ob.asks()[10::-1]:
                print(f'{p:<10}{s:>10.3f}')
            print('==== Order Book ====')
            for p, s in ob.bids()[:10]:
                print(f'{p:<10}{s:>10.3f}')
            print('')
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


class WebsocketBase:
    def __init__(self, url, enable_auth=False):
        self.log = logging.getLogger(self.__class__.__name__)
        self.url = url

        self.is_open = False
        self.is_auth = None  # None: before auth, True: success, False: failed
        self.is_auth_enabled = enable_auth

        self.__after_open_cb = []
        self.__after_auth_cb = []
        self.__ch_cb_map = {}

        run_forever_nonblocking(self.__worker, self.log, 3)

    def add_after_open_cb(self, cb):
        self.__after_open_cb.append(cb)
        if self.is_open:
            cb()  # call immediately if already opened

    def add_after_auth_cb(self, cb):
        self.__after_auth_cb.append(cb)
        if self.is_auth:
            cb()  # call immediately if already authenticated

    def wait_open(self, timeout=10):
        ts = time.time()
        while True:
            if not self.is_open:
                if time.time() - ts > timeout:
                    raise Exception('Waiting open timeout')
            else:
                return
            time.sleep(0.1)

    def wait_auth(self, timeout=10):
        if not self.is_auth_enabled:
            raise Exception('Auth is not enabled')

        ts = time.time()
        while True:
            if self.is_auth is None:
                if time.time() - ts > timeout:
                    raise Exception('Waiting auth timeout')
            elif self.is_auth:
                return
            else:
                raise Exception('Auth failed')
            time.sleep(0.1)

    def send(self, msg):
        self.ws.send(json.dumps(msg))
        self.log.debug(f'send: {msg}')

    def subscribe(self, ch, cb, ch_name=None):
        self.__ch_cb_map[ch_name or ch] = cb
        self._subscribe(ch)

    def _on_open(self):
        self.log.info('open websocket')
        self.is_open = True
        self.__ch_cb_map = {}
        try:
            for cb in self.__after_open_cb:
                cb()

            def worker():
                try:
                    self._authenticate()
                    self.wait_auth()
                    for cb in self.__after_auth_cb:
                        cb()
                except:
                    self.log.error(traceback.format_exc())

            if self.is_auth_enabled:
                threading.Thread(target=worker).start()
        except:
            self.log.error(traceback.format_exc())

    def _on_close(self):
        self.is_open = False
        self.is_auth = None
        self.log.info('close websocket')

    def _on_message(self, msg):
        self.log.debug(f'recv: {msg}')

    def _on_error(self, err):
        self.log.error(f'recv: {err}')

    def _authenticate(self):
        assert False
        return 0

    def _subscribe(self, ch):
        assert False
        return 0

    def _handle_ch_message(self, ch, msg):
        try:
            self.__ch_cb_map[ch](msg)
        except:
            self.log.error(traceback.format_exc())

    def __worker(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_message=self._on_message,
            on_error=self._on_error)
        self.ws.run_forever()


class TradeBase:
    def __init__(self):
        self.ltp = None
        self.cb = []

    def add_cb(self, cb):
        self.cb.append(cb)

    def remove_Cb(self, cb):
        self.cb.remove(cb)

    def _trigger_cb(self, ts, price, size):
        for cb in self.cb:
            cb(ts, price, size)


class OrderbookBase:
    def __init__(self):
        self.cb = []
        self.init()

    def init(self):
        self.sd_bids = SortedDict()
        self.sd_asks = SortedDict()

    def bids(self):
        return self.sd_bids.values()

    def asks(self):
        return self.sd_asks.values()

    def add_cb(self, cb):
        self.cb.append(cb)

    def remove_Cb(self, cb):
        self.cb.remove(cb)

    def _trigger_cb(self):
        for cb in self.cb:
            cb()


class PositionGroupBase(dict):
    def __init__(self):
        super().__init__()
        self.__dict__ = self
        self.position = 0
        self.gain = 0
        self.pnl = 0
        self.unrealized_pnl = 0

    def update(self, price, size):
        pos, gain = size, price * -size
        new_pos = self.position + pos

        if self.position * size >= 0:
            new_gain = self.gain + gain
        else:
            p, g = (pos, gain) if new_pos * \
                pos > 0 else (self.position, self.gain)
            new_gain = g * new_pos / p

        self.pnl += self.gain + gain - new_gain
        self.position = new_pos
        self.gain = new_gain
        self.update_unrealized_pnl(price)

    def update_unrealized_pnl(self, price):
        self.unrealized_pnl = self.gain + price * self.position
