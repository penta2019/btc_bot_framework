import time
import logging
import json
import traceback
import threading
import asyncio

import websockets


def new_event_loop(name):
    loop = asyncio.new_event_loop()
    threading.Thread(
        target=lambda: loop.run_forever(),
        daemon=True, name=name).start()
    return loop


class WebsocketBase:
    ENDPOINT = ''
    _loop = new_event_loop('WebsocketBase_asyncio')

    def __init__(self, key=None, secret=None):
        self.log = logging.getLogger(self.__class__.__name__)

        self.url = self.ENDPOINT
        self.key = key
        self.secret = secret

        self.running = True
        self.is_open = False
        self.is_auth = None  # None: before auth, True: success, False: failed

        self._ws = None
        self._request_id = 1  # next request id
        self._request_table = {}
        self._ch_cb = {}

        self.__lock = threading.Lock()
        self.__after_open_cb = []
        self.__after_auth_cb = []

        if self.key and self.secret:
            self.add_after_open_callback(self._authenticate)

        asyncio.run_coroutine_threadsafe(self.__worker(), WebsocketBase._loop)

    def stop(self):
        self.running = False
        asyncio.run_coroutine_threadsafe(self._ws.close(), WebsocketBase._loop)

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

    def send_raw(self, msg):
        asyncio.run_coroutine_threadsafe(
            self._ws.send(msg), WebsocketBase._loop)
        self.log.debug(f'send_raw: {msg}')

    def send(self, msg):
        asyncio.run_coroutine_threadsafe(
            self._ws.send(json.dumps(msg)), WebsocketBase._loop)
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
            asyncio.run_coroutine_threadsafe(
                self._ws.close(), WebsocketBase._loop)

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
        self.log.info(f'open websocket: {self.url}')
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

    async def __worker(self):
        while True:
            try:
                self._on_init()

                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    self._on_open()
                    while True:
                        try:
                            msg = await ws.recv()
                            self._on_message(msg)
                        except websockets.ConnectionClosed:
                            break
                        except Exception as e:
                            self._on_error(e)

                self._on_close()
            except Exception:
                self.log.error(traceback.format_exc())

            self._ws = None
            if not self.running:
                break
            await asyncio.sleep(5)
