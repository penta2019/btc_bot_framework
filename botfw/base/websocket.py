import time
import logging
import json
import traceback

import websocket

from ..etc.util import run_forever_nonblocking


class WebsocketBase:
    def __init__(self, url):
        self.log = logging.getLogger(self.__class__.__name__)
        self.url = url

        self.is_open = False
        self.is_auth = None  # None: before auth, True: success, False: failed

        self.__after_open_cb = []
        self.__after_auth_cb = []

        run_forever_nonblocking(self.__worker, self.log, 3)

    def add_after_open_callback(self, cb):
        self.__after_open_cb.append(cb)
        if self.is_open:
            cb()  # call immediately if already opened

    def add_after_auth_callback(self, cb):
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

    def _on_auth(self, success):
        if success:
            self.log.info('authentication succeeded')
            self.is_open = True
            for cb in self.__after_auth_cb:
                try:
                    cb()
                except Exception:
                    self.log.error(traceback.format_exc())
        else:
            self.log.info('authentication failed')
            self.is_open = True

    def _on_open(self):
        self.log.info('open websocket')
        self.is_open = True
        for cb in self.__after_open_cb:
            try:
                cb()
            except Exception:
                self.log.error(traceback.format_exc())

    def _on_close(self):
        self.is_open = False
        self.is_auth = None
        self.log.info('close websocket')

    def _on_message(self, msg):
        self.log.debug(f'recv: {msg}')

    def _on_error(self, err):
        self.log.error(f'recv: {err}')

    def __worker(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_message=self._on_message,
            on_error=self._on_error)
        self.ws.run_forever()
