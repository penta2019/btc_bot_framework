import time
import logging

from sortedcontainers import SortedDict

from ..etc.util import setup_logger


def test_orderbook(ob, trace=False, log_level=logging.INFO):
    setup_logger(log_level)
    ob.wait_initialized()
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


class OrderbookBase:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.cb = []
        self.init()

    def init(self):
        self.sd_bids = SortedDict()
        self.sd_asks = SortedDict()

    def wait_initialized(self, timeout=60):
        ts = time.time()
        count = 0
        while True:
            if not self.asks() or not self.bids():
                if time.time() - ts > timeout:
                    self.log.error(f'timeout({timeout}s)')
                    return
                else:
                    count += 1
                    if count % 5 == 0:
                        self.log.info('waiting to be initialized')
            else:
                return
            time.sleep(1)

    def bids(self):
        return self.sd_bids.values()

    def asks(self):
        return self.sd_asks.values()

    def add_callback(self, cb):
        self.cb.append(cb)

    def remove_callback(self, cb):
        self.cb.remove(cb)

    def _trigger_callback(self):
        for cb in self.cb:
            cb()
