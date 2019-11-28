import time
import datetime
import logging
import threading
import traceback


def unix_time_from_ISO8601Z(date):
    td = datetime.datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
    td = td.replace(tzinfo=datetime.timezone.utc)
    ts = td.timestamp()
    ts += float('0.' + date[20:-1])
    return ts


def setup_logger(level=logging.INFO):
    log = logging.getLogger()
    log.setLevel(level)
    fmt = MillisecondFormatter(
        '[%(asctime)s %(levelname).1s %(name)s] %(message)s')
    handler = logging.StreamHandler()
    # handler = logging.FileHandler(filename="test.log")
    handler.setFormatter(fmt)
    log.addHandler(handler)


def run_forever(callback, log, sleep, exception_sleep=5):
    while True:
        try:
            callback()
        except StopRunForever:
            break
        except Exception as e:
            log.error(type(e).__name__ + ': ' + str(e)[:256])
            log.debug(traceback.format_exc())
            time.sleep(exception_sleep)
        time.sleep(sleep)


def run_forever_nonblocking(callback, log, sleep, exception_sleep=5):
    thread = threading.Thread(
        name=log.name, target=run_forever,
        args=(callback, log, sleep, exception_sleep))
    thread.daemon = True
    thread.start()


class StopRunForever(Exception):
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
