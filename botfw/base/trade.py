import logging
import time

import websocket

from ..etc.util import setup_logger


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
