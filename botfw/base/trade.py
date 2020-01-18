import logging
import time

import websocket

from ..etc.util import setup_logger


def test_trade(t, trace=False, log_level=logging.INFO):
    websocket.enableTrace(trace)
    setup_logger(log_level)
    try:
        t.add_callback(lambda ts, p, s: print(f'{ts:.3f} {p:.1f} {s:+.3f}'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


class TradeBase:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.ltp = None
        self.cb = []

    def wait_initialized(self, timeout=60):
        ts = time.time()
        count = 0
        while True:
            if not self.ltp:
                if time.time() - ts > timeout:
                    self.log.error(f'timeout({timeout}s)')
                else:
                    count += 1
                    if count % 5 == 0:
                        self.log.info('waiting to be initialized')
            else:
                return
            time.sleep(1)

    def add_callback(self, cb):
        self.cb.append(cb)

    def remove_callback(self, cb):
        self.cb.remove(cb)

    def _trigger_callback(self, ts, price, size):
        for cb in self.cb:
            cb(ts, price, size)
