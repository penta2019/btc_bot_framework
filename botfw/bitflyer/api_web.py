import json
import logging
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .api import BitflyerApi


class BitflyerApiWithWebOrder(BitflyerApi):
    def __init__(self, ccxt_config, login_id, password, account_id,
                 device_id=None, device_token=None):
        super().__init__(ccxt_config)
        self.load_markets()
        self.api = BitflyerWebApi(
            login_id, password, account_id, device_id, device_token)
        self.api.login()

    def create_order(self, symbol, type_, side, amount, price=None, params={}):
        try:
            symbol = self.markets[symbol]['id']
            type_ = type_.upper()
            side = side.upper()
            res = self.api.send_order(
                symbol, type_, side, amount, price, **params)
            # {'status': 0,
            #  'error_message': None,
            #  'data': {'order_ref_id': 'JRF20180509-220225-476540'}}
            #
            # 0: success
            # -501: session expired
            # -153: minimum size >= 0.01
            # ...
        finally:
            path = 'sendorder'
            if path in self.count:
                self.count[path] += 1
            else:
                self.count[path] = 1

            self.capacity -= 1

            if self.log.level <= logging.DEBUG:
                self.log.debug(
                    f'request: sendorder '
                    f'{symbol} {type_} {side} {amount} {price} {params}')

        st, err = res['status'], res['error_message']
        if st != 0:
            if res['status'] == -501:
                self.api.login()
            raise Exception(f'create_order: {st}, {err}')

        return {'id': res['data']['order_ref_id']}


class BitflyerWebApi:
    def __init__(self, login_id, password, account_id,
                 device_id=None, device_token=None):
        self.login_id = login_id
        self.password = password
        self.account_id = account_id
        self.device_id = device_id
        self.device_token = device_token

        self.domain = 'lightning.bitflyer.jp'
        self.url = 'https://lightning.bitflyer.jp/api/trade'
        self.headers = {
            'User-agent': 'Mozilla/5.0 (X11; Linux x86_64) \
             AppleWebKit/537.36 (KHTML, like Gecko) \
             Chrome/65.0.3325.181 Safari/537.36',
            'Content-Type': 'application/json; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.timeout = (10, 10)
        self.session = None

    def set_timeout(self, sec):
        self.timeout = (sec, sec)

    def login(self):
        s = requests.Session()
        if self.device_id and self.device_token:
            s.cookies.set(
                'device_id', self.device_id, domain=self.domain)
            s.cookies.set(
                'device_token', self.device_token, domain=self.domain)

        r = s.get('https://' + self.domain)
        params = {
            'LoginId': self.login_id,
            'password': self.password,
            '__RequestVerificationToken':
                BeautifulSoup(r.text, 'html.parser').find(
                    attrs={'name': '__RequestVerificationToken'}).get('value'),
        }
        s.post('https://' + self.domain, data=params)
        self.session = s

    def post(self, path, param):
        url = self.url + path
        param['account_id'] = self.account_id
        param['lang'] = 'ja'
        data = json.dumps(param).encode('utf-8')
        res = self.session.post(url, data=data, headers=self.headers,
                                timeout=self.timeout)
        return json.loads(res.text)

    def get(self, path, param=None):
        if not param:
            param = {}
        param['account_id'] = self.account_id
        param['lang'] = 'ja'
        param['v'] = '1'
        url = self.url + path + '?' + urlencode(param)
        res = self.session.get(url, headers=self.headers,
                               timeout=self.timeout)
        return json.loads(res.text)

    def param(self, symbol, ord_type, side, price=0, size=0,
              minute_to_expire=43200, trigger=0, offset=0):
        return {
            'product_code': symbol,
            'ord_type': ord_type,
            'side': side,
            'price': price,
            'size': size,
            'minuteToExpire': minute_to_expire,
            'trigger': trigger,
            'offset': offset,
        }

    def health(self, symbol):
        param = {'product_code': symbol}
        return self.get('/gethealth', param)

    def ticker(self, symbol):
        param = {
            'product_code': symbol,
            'offset_seconds': 300,
            'v': 1,
        }
        return self.get('/ticker', param)

    def all_tickers(self):
        param = {'v': 1}
        return self.get('/ticker/all', param)

    def ticker_data(self, symbol):
        param = {'product_code': symbol}
        return self.get('/tickerdata', param)

    def send_order(self, symbol, type_, side, size, price=None,
                   minute_to_expire=43200, time_in_force='GTC'):
        param = {
            'product_code': symbol,
            'ord_type': type_,
            'side': side,
            'price': price,
            'size': size,
            'minuteToExpire': minute_to_expire,
            'time_in_force': time_in_force,
            'is_check': False,
        }
        return self.post('/sendorder', param)

    def cancel_order(self, symbol, order_id, parent_order_id):
        param = {
            'product_code': symbol,
            'order_id': order_id,
            'parent_order_id': parent_order_id,
        }
        return self.post('/cancelorder', param)

    def cancel_all_order(self, symbol):
        param = {
            'product_code': symbol,
        }
        return self.post('/cancelallorder', param)

    def get_collateral(self, symbol):
        param = {
            'product_code': symbol,
        }
        return self.post('/getmyCollateral', param)

    def my_board_orders(self, symbol):
        param = {
            'product_code': symbol,
        }
        return self.post('/getMyBoardOrders', param)

    def my_child_order(self, symbol, order_id):
        param = {
            'product_code': symbol,
            'order_id': order_id,
        }
        return self.post('/getMyChildOrder', param)

    def my_executions(self, symbol, count):
        param = {
            'product_code': symbol,
            'number_of_executions': count,
        }
        return self.post('/getmyexecutionhistory', param)

    def send_chat(self, message):
        param = {
            'channel': 'MAIN_JP',
            'nickname': '',
            'message': message,
        }
        return self.post('/sendchat', param)
