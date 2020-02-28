import time
import datetime
import decimal
import logging
import threading
import traceback
import hmac
import hashlib

import ccxt

no_traceback_exceptions = (ccxt.NetworkError)


def unix_time_from_ISO8601Z(date):
    td = datetime.datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
    td = td.replace(tzinfo=datetime.timezone.utc)
    ts = td.timestamp()
    ts += float('0.' + date[20:-1])
    return ts


def decimal_add(x0, x1):
    return float(decimal.Decimal(str(x0)) + decimal.Decimal(str(x1)))


def hmac_sha256(key, msg):
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()


def setup_logger(level=logging.INFO):
    log = logging.getLogger()
    log.setLevel(level)
    fmt = MillisecondFormatter(
        '[%(asctime)s %(levelname).1s %(name)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    log.addHandler(handler)


def run_forever(cb, log, sleep=0, exception_sleep=5):
    while True:
        try:
            cb()
        except StopRunForever:
            break
        except no_traceback_exceptions as e:
            log.error(f'{type(e).__name__}: {e}')
        except Exception:
            log.error(traceback.format_exc())
            time.sleep(exception_sleep)
        time.sleep(sleep)


def run_forever_nonblocking(cb, log, sleep, exception_sleep=5):
    thread = threading.Thread(
        name=log.name, target=run_forever,
        args=(cb, log, sleep, exception_sleep))
    thread.daemon = True
    thread.start()
    return thread


class StopRunForever(BaseException):
    pass


class MillisecondFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.datetime.fromtimestamp(record.created)
        t = ct.strftime('%H:%M:%S')
        return f'{t}.{record.msecs:03.0f}'


class Timer:
    def __init__(self, interval):
        self.interval = interval
        self.ts = time.time()

    def is_interval(self):
        now = time.time()
        if now - self.ts > self.interval:
            self.ts = now
            return True
        return False
