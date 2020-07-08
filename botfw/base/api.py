import logging
import threading

import ccxt

from ..etc.util import run_forever_nonblocking


class ApiBase:
    MAX_API_CAPACITY = 60
    API_PER_SECOND = 1
    _instance = None
    _lock = threading.Lock()
    _ccxt_class = ccxt.Exchange

    @classmethod
    def ccxt_instance(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = cls._ccxt_class()
                getattr(cls._instance, 'load_markets')()
        return cls._instance

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.capacity = self.MAX_API_CAPACITY
        self.count = {}
        run_forever_nonblocking(self.__worker, self.log, 1)

        # silence linter
        self.sign = getattr(self, 'sign')
        self.fetch = getattr(self, 'fetch')

    def fetch_position(self, symbol):
        assert False
        return 0

    def request(self, path, api='public', method='GET', params={},
                headers=None, body=None):
        try:
            request = self.sign(
                path, api, method, params, headers, body)
            res = self.fetch(
                request['url'], request['method'],
                request['headers'], request['body'])
        finally:
            if self.log.level <= logging.DEBUG:
                self.log.debug(
                    f'request: {path} {api} {method} '
                    f'{params} {headers} {body}')

            if path in self.count:
                self.count[path] += 1
            else:
                self.count[path] = 1

            self.capacity -= 1

        return res

    def __worker(self):
        if self.capacity < self.MAX_API_CAPACITY:
            self.capacity += self.API_PER_SECOND
