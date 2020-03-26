import time
import logging
import json
import traceback
import threading

import websocket

from ..etc.util import run_forever_nonblocking, StopRunForever


class WebsocketBase:
    ENDPOINT = None

    def __init__(self, key=None, secret=None):
        self.log = logging.getLogger(self.__class__.__name__)

        self.url = self.ENDPOINT
        self.key = key
        self.secret = secret

        self.ws = None
        self.running = True

        self.is_open = False
        self.is_auth = None  # None: before auth, True: success, False: failed

        self._request_id = 1  # next request id
        self._request_table = {}
        self._ch_cb = {}

        self.__lock = threading.Lock()
        self.__after_open_cb = []
        self.__after_auth_cb = []

        if self.key and self.secret:
            self.add_after_open_callback(self._authenticate)

        run_forever_nonblocking(self.__worker, self.log, 3)

    def stop(self):
        self.running = False
        self.ws.close()

    def add_after_open_callback(self, cb):
        with self.__lock:
            self.__after_open_cb.append(cb)
            if self.is_open:
                cb()  # call immediately if already opened

    def add_after_auth_callback(self, cb):
        with self.__lock:
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

    def subscribe(self, ch, cb, auth=False):
        self._ch_cb[ch] = cb
        if auth:
            self.add_after_auth_callback(lambda: self._subscribe(ch))
        else:
            self.add_after_open_callback(lambda: self._subscribe(ch))

    def _set_auth_result(self, success):
        if success:
            self.log.info('authentication succeeded')
            with self.__lock:
                self.is_auth = True
                self._run_callbacks(self.__after_auth_cb)
        else:
            self.log.error('authentication failed')
            self.is_auth = False
            self.ws.close()

    def _run_callbacks(self, cbs, *args):
        for cb in cbs:
            try:
                cb(*args)
            except Exception:
                self.log.error(traceback.format_exc())

    def _subscribe(self, ch):
        assert False

    def _authenticate(self):
        assert False

    def _handle_message(self, msg):
        assert False

    def _on_init(self):
        pass

    def _on_open(self):
        self.log.info('open websocket')
        self._next_id = 1
        self._request_table = {}
        with self.__lock:
            self.is_open = True
            self._run_callbacks(self.__after_open_cb)

    def _on_close(self):
        self.is_open = False
        self.is_auth = None
        self.log.info('close websocket')

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            self._handle_message(msg)
        except Exception:
            self.log.error(traceback.format_exc())

    def _on_error(self, err):
        self.log.error(f'recv: {err}')

    def __worker(self):
        self._on_init()
        self.log.debug(f'create websocket: url={self.url}')
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_message=self._on_message,
            on_error=self._on_error)
        self.ws.run_forever(ping_interval=60)

        if not self.running:
            raise StopRunForever
