import json
import hmac
import hashlib
import time
import decimal

import ccxt


def decimal_add(x0, x1):
    return float(decimal.Decimal(str(x0)) + decimal.Decimal(str(x1)))

# ### symbols ###
# spot: BTC ETH BCH LTC XRP
# future: BTC_JPY ETH_JPY BCH_JPY LTC_JPY XRP_JPY

# ### Usage ###
# from botfw.gmocoin.api_ccxt import gmocoin
# ccxt_config = {
#     'apiKey': 'YOUR_API_KEY',
#     'secret': 'YOUR_API_SECRET',
# }
# gmo = gmocoin(ccxt_config)

# import pprint; pprint.pprint(dir(gmo))  # show all methods and variables
# import logging; logging.basicConfig(level=logging.DEBUG)  # for debugging

# res = gmo.fetch_ticker('BTC_JPY')

# res = gmo.create_order('BTC_JPY', 'limit', 'buy', 0.01, 1000000)
# order_id = res['id']

# res = gmo.fetch_open_orders('BTC_JPY')

# res = gmo.cancel_order(order_id)

# ### custom exchange API (not unified ccxt API) ###
# res = gmo.private_get_openpositions(params={'symbol': 'BTC_JPY'})

# # websocket key (valid for 60 minutes)
# res = gmo.private_post_ws_auth()
# websocket_key = res['data']

# # keep-alive websocket key
# res = gmo.private_put_ws_auth(params={'token': websocket_key})

# # see also(https://api.coin.z.com/docs/?python)


class gmocoin(ccxt.Exchange):
    '''
    CCXT compatible API wrapper
    GMOCoin is not supported by ccxt currently.
    '''

    def describe(self):
        return self.deep_extend(super().describe(), {
            'id': 'gmocoin',
            'name': 'GMO Coin',
            'countries': ['JP'],
            'version': 'v1',
            'rateLimit': 1000,
            'has': {
                'CORS': False,
                'withdraw': False,
                'fetchMyTrades': True,
                'fetchOrders': False,
                'fetchOrder': True,
                'fetchOpenOrders': True,
                'fetchClosedOrders': False,
            },
            'urls': {
                'logo': 'https://coin.z.com/corp_imgs/logo.svg',
                'api': 'https://api.coin.z.com',
                'www': 'https://coin.z.com/jp',
                'doc': 'https://api.coin.z.com/docs/en',
            },
            'api': {
                'public': {
                    'get': [
                        'status',
                        'ticker',
                        'orderbooks',
                        'trades',
                    ],
                },
                'private': {
                    'get': [
                        'account/margin',
                        'account/assets',
                        'orders',
                        'activeOrders',
                        'executions',
                        'latestExecutions',
                        'openPositions',
                        'positionSummary',

                    ],
                    'post': [
                        'order',
                        'changeOrder',
                        'cancelOrder',
                        'closeOrder',
                        'closeBulkOrder',
                        'changeLosscutPrice',
                        'ws-auth',
                    ],
                    'put': [
                        'ws-auth',
                    ],
                    'delete': [
                        'ws-auth',
                    ]
                },
            },
            'fees': {
                'trading': {
                    'maker': -0.01 / 100,
                    'taker': 0.05 / 100,
                },
            },
        })

    def fetch_markets(self, params={}):
        res = getattr(self, 'public_get_ticker')()
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        result = []
        for market in res['data']:
            id_ = market['symbol']
            currencies = id_.split('_')
            symbol = id_
            if len(currencies) == 1:
                type_ = 'spot'
                base_id = currencies[0]
                quote_id = 'JPY'
                fees = self.fees
                maker = fees['trading']['maker']
                taker = fees['trading']['taker']
                spot = True
                future = False
            else:
                type_ = 'future'
                base_id = currencies[0]
                quote_id = currencies[1]
                maker = 0
                taker = 0
                spot = False
                future = True
            base = base_id
            quote = quote_id

            result.append({
                'id': id_,
                'symbol': symbol,
                'base': base,
                'quote': quote,
                'baseId': base_id,
                'quoteId': quote_id,
                'maker': maker,
                'taker': taker,
                'type': type_,
                'spot': spot,
                'future': future,
                'info': market,
            })
        return result

    def fetch_balance(self, params={}):
        self.load_markets()
        res = getattr(self, 'private_get_account_assets')()
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        result = {'info': res}
        for balance in res['data']:
            currency_id = balance['symbol']
            code = currency_id
            account = self.account()
            account['total'] = float(balance['amount'])
            account['free'] = float(balance['available'])
            result[code] = account
        return self.parse_balance(result)

    def fetch_order_book(self, symbol, limit=None, params={}):
        self.load_markets()
        request = {
            'symbol': self.market_id(symbol),
        }
        res = getattr(self, 'public_get_orderbooks')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        orderbook = res['data']
        return self.parse_order_book(
            orderbook, None, 'bids', 'asks', 'price', 'size')

    def fetch_ticker(self, symbol, params={}):
        self.load_markets()
        request = {
            'symbol': self.market_id(symbol),
        }
        res = getattr(self, 'public_get_ticker')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        ticker = res['data'][0]
        timestamp = self.parse8601(ticker['timestamp'])
        last = float(ticker['last'])
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': float(ticker['high']),
            'low': float(ticker['low']),
            'bid': float(ticker['bid']),
            'bidVolume': None,
            'ask': float(ticker['ask']),
            'askVolume': None,
            'vwap': None,
            'open': None,
            'close': last,
            'last': last,
            'previousClose': None,
            'change': None,
            'percentage': None,
            'average': None,
            'baseVolume': float(ticker['volume']),
            'quoteVolume': None,
            'info': ticker,
        }

    def parse_trade(self, trade, market=None):
        side = trade['side'].lower()
        timestamp = self.parse8601(trade['timestamp'])
        price = float(trade['price'])
        amount = float(trade['size'])
        fee = float(trade['fee']) if 'fee' in trade else None
        cost = None
        if amount and price:
            cost = price * amount
        id_ = trade.get('executionId')
        order = trade.get('orderId')
        symbol = market['symbol'] if market else None
        return {
            'id': id_,
            'info': trade,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'symbol': symbol,
            'order': order,
            'type': None,
            'side': side,
            'takerOrMaker': None,
            'price': price,
            'amount': amount,
            'cost': cost,
            'fee': fee,
        }

    def fetch_trades(self, symbol, since=None, limit=None, params={}):
        self.load_markets()
        market = self.market(symbol)
        request = {
            'symbol': market['id'],
        }
        res = getattr(self, 'public_get_trades')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])

        trades = res['data'].get('list', [])
        return self.parse_trades(trades, market, since, limit)

    def create_order(self, symbol, type_, side, amount, price=None, params={}):
        self.load_markets()
        request = {
            'symbol': symbol,
            'side': side.upper(),
            'executionType': type_.upper(),
            'size': str(amount),
        }
        if price:
            request['price'] = str(price)
        res = getattr(self, 'private_post_order')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.InvalidOrder(res['messages'])

        return {
            'info': res,
            'id': res['data'],
        }

    def cancel_order(self, id_, symbol=None, params={}):
        self.load_markets()
        request = {
            'orderId': id_,
        }
        res = getattr(self, 'private_post_cancelorder')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        return res

    def parse_order_status(self, status):
        statuses = {
            'CANCELED': 'canceled',
            'EXPIRED': 'canceled',
            'EXECUTED': 'closed',
        }
        return statuses[status] if status in statuses else 'open'

    def parse_order(self, order, market=None):
        timestamp = self.parse8601(order['timestamp'])
        amount = float(order['size'])
        filled = float(order['executedSize'])
        remaining = decimal_add(amount, -filled)
        price = float(order['price'])
        cost = price * filled
        status = self.parse_order_status(order['status'])
        type_ = order['executionType'].lower()
        side = order['side'].lower()
        symbol = order['symbol']
        id_ = order['orderId']
        return {
            'id': id_,
            'info': order,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'lastTradeTimestamp': None,
            'status': status,
            'symbol': symbol,
            'type': type_,
            'side': side,
            'price': price,
            'cost': cost,
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'fee': None,
        }

    # def fetch_orders(self, symbol=None, since=None, limit=100, params={}):
    #     pass

    def fetch_open_orders(self, symbol=None, since=None, limit=100, params={}):
        if symbol is None:
            raise ccxt.ArgumentsRequired(
                self.id + ' fetch_open_orders() requires a `symbol` argument')
        self.load_markets()
        market = self.market(symbol)
        request = {
            'symbol': market['id'],
            'count': limit,
        }
        res = getattr(self, 'private_get_activeorders')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        orders = res['data'].get('list', [])
        return self.parse_orders(orders, market, since, limit)

    # def fetch_closed_orders(
    #         self, symbol=None, since=None, limit=100, params={}):
    #     pass

    def fetch_order(self, id_, symbol=None, params={}):
        self.load_markets()
        request = {
            'orderId': id_,
        }
        res = getattr(self, 'private_get_orders')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        orders = res['data'].get('list')
        if not orders:
            raise ccxt.OrderNotFound(f'{self.id} No order found with id {id_}')
        return self.parse_order(orders[0])

    def fetch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        if symbol is None:
            raise ccxt.ArgumentsRequired(
                self.id + ' fetchMyTrades requires a `symbol` argument')
        self.load_markets()
        market = self.market(symbol)
        request = {
            'symbol': market['id'],
        }
        res = getattr(self, 'private_get_latestexecutions')(
            self.extend(request, params))
        if res['status'] != 0:
            raise ccxt.BaseError(res['messages'])
        trades = res['data'].get('list', [])
        return self.parse_trades(trades, market, since, limit)

    # def withdraw(self, code, amount, address, tag=None, params={}):
    #     pass

    def sign(self, path, api='public', method='GET',
             params={}, headers=None, body=None):
        path = '/v1/' + path
        if method == 'GET' and params:
            url_param = '?' + self.urlencode(params)
        else:
            url_param = ''
        url = f'{self.urls["api"]}/{api}{path}{url_param}'

        body = json.dumps(params) if method != 'GET' else None

        if api == 'private':
            self.check_required_credentials()
            timestamp = str(int(time.time()) * 1000)

            body_sign = body if method == 'POST' else ''
            sign = hmac.new(
                self.secret.encode(),
                f'{timestamp}{method}{path}{body_sign}'.encode(),
                hashlib.sha256).hexdigest()
            headers = {
                'API-KEY': self.apiKey,
                'API-TIMESTAMP': timestamp,
                'API-SIGN': sign,
            }

        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    # silence linter
    if False:
        urls = {}
