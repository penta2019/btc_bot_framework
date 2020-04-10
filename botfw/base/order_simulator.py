import time
import logging
from decimal import Decimal, ROUND_FLOOR

from sortedcontainers import SortedList

from ..etc.util import decimal_add, run_forever_nonblocking
from . import order as od


def bitflyer_fee_func(symbol, side, price, amount, fee_rate):
    ffb = 0  # fee from balance
    if symbol == 'BTC/JPY':
        f = Decimal(str(amount)) * Decimal(str(fee_rate))
        ffb = float(f.quantize(Decimal('0.00000001'), ROUND_FLOOR))
    info = {'commission': ffb, 'sfd': 0}
    return price * amount * fee_rate, ffb, info


class SymbolSimulator:
    def __init__(
            self, order_manager, market, trade, orderbook):
        self.order_manager = order_manager
        self.trade = trade
        self.orderbook = orderbook

        self.symbol = market['symbol']
        self.spot = market.get('spot') or False
        self.taker_fee = market['taker']
        self.maker_fee = market['maker']
        self.delay_create_order = 0.1
        self.delay_cancel_order = 0.1
        self.delay_edit_order = 0.1

        self.position = 0
        self.buy = SortedList(key=lambda o: -o.price)
        self.sell = SortedList(key=lambda o: o.price)
        self.pending = []      # [order]
        self.canceling = []    # [order]

        self.trade.add_callback(self.trade_callback)

    def create_order(self, o):
        if self.spot and o.side == od.SELL:  # check balance
            r = 0
            for o2 in self.sell:
                r = decimal_add(r, decimal_add(o2.amount, -o2.filled))
            for o2 in self.pending:
                if o2.side == od.SELL:
                    r = decimal_add(r, decimal_add(o2.amount, -o2.filled))

            total_sell = decimal_add(r, o.amount)
            fee_from_balance = self.order_manager.fee_func(
                o.symbol, o.side, 0, o.amount + r, self.taker_fee)[1]
            print(self.position, total_sell, fee_from_balance,
                  decimal_add(total_sell, fee_from_balance))
            if self.position < decimal_add(total_sell, fee_from_balance):
                raise Exception(
                    'insufficient balance: '
                    'balance < total_sell_size + fee_from_balance ('
                    f'balance={self.position}, '
                    f'total_sell={total_sell}, '
                    f'fee_from_balance={fee_from_balance})')

        self.pending.append(o)

    def cancel_order(self, o):
        if o not in self.buy and o not in self.sell:
            self.order_manager.log.error(
                f'cancel failed: order {o.id} not found')
            return
        self.canceling.append(o)

    def edit_order(self, o, amount, price):
        amount = amount or o.amount
        price = price or o.price

        time.sleep(self.delay_edit_order)
        if amount < o.filled:
            raise Exception('amount is smaller then filled size')
        if o.state in [od.CLOSED, od.CANCELED]:
            raise Exception('order is already closed or canceled')

        l = self.buy if o.side == od.BUY else self.sell
        l.remove(o)
        o.amount = amount
        o.price = price
        self.pending.append(o)

    def to_execute_size(self, price, size):
        qp = self.order_manager.quote_prec
        return size if qp is None else round(price * size, qp)

    def execute(self, o, ts, price, max_size, fee_rate):
        remaining = decimal_add(o.amount, -o.filled)
        executed = min(remaining, max_size)
        o.filled = decimal_add(o.filled, executed)
        self.position = decimal_add(
            self.position, -executed if o.side == od.SELL else executed)
        if o.amount == o.filled:
            o.state, o.state_ts, o.close_ts = od.CLOSED, ts, ts

        fee, fee_from_balance, info = self.order_manager.fee_func(
            o.symbol, o.side, price, executed, fee_rate)
        if fee_from_balance != 0:
            self.position = decimal_add(self.position, -fee_from_balance)

        if o.event_cb:
            size = -executed if o.side == od.SELL else executed
            o.event_cb(od.OrderEvent(
                o.id, ts, od.EVENT_EXECUTION, price, size, fee, info=info))
        return executed

    def trade_callback(self, ts, price, size):
        size = self.to_execute_size(price, size)
        closed = []
        now = time.time()

        # handle pending orders
        ts0 = ts - self.delay_create_order
        for o in [o for o in self.pending if ts0 > o.state_ts]:
            o.id = id(o)
            o.state, o.state_ts, o.open_ts = od.OPEN, ts, ts
            self.pending.remove(o)
            self.order_manager.orders[o.id] = o
            self.order_manager.last_update_ts = now

            if o.event_cb:
                o.event_cb(od.OrderEvent(o.id, ts, od.EVENT_OPEN))

            # simulate take execution
            worst_price = price
            if o.side == od.BUY:
                for p, s in self.orderbook.asks():
                    if (o.price and p >= o.price) or o.amount == o.filled:
                        break
                    s = self.to_execute_size(p, s)
                    self.execute(o, ts, p, s, self.taker_fee)
                    worst_price = p
            elif o.side == od.SELL:
                for p, s in self.orderbook.bids():
                    if (o.price and p <= o.price) or o.amount == o.filled:
                        break
                    s = self.to_execute_size(p, s)
                    self.execute(o, ts, p, s, self.taker_fee)
                    worst_price = p
            else:
                assert False

            if o.amount != o.filled:  # order is remaining
                if o.price:  # limit
                    if o.side == od.BUY:
                        self.buy.add(o)
                    elif o.side == od.SELL:
                        self.sell.add(o)
                    else:
                        assert False
                else:  # market
                    # when amount is big enough to take all orders on orderbook
                    self.execute(o, ts, worst_price, o.amount, self.taker_fee)

        # simulate make execution
        if size < 0:  # buy(taker=sell)
            remaining = -size
            for o in self.buy:
                if o.price <= price or remaining == 0:
                    break
                executed = self.execute(
                    o, ts, o.price, remaining, self.maker_fee)
                remaining = decimal_add(remaining, -executed)
                if o.state == od.CLOSED:
                    closed.append(o)
                self.order_manager.last_update_ts = now
        else:  # sell(taker=BUY)
            remaining = size
            for o in self.sell:
                if o.price >= price or remaining == 0:
                    break
                executed = self.execute(
                    o, ts, o.price, remaining, self.maker_fee)
                remaining = decimal_add(remaining, -executed)
                if o.state == od.CLOSED:
                    closed.append(o)
                self.order_manager.last_update_ts = now

        # handle canceling orders
        ts0 = ts - self.delay_cancel_order
        for o in [o for o in self.canceling if ts0 > o.state_ts]:
            self.canceling.remove(o)
            if o.state not in [od.CLOSED, od.CANCELED] \
                    and (o in self.buy or o in self.sell):
                o.state, o.state_ts, o.close_ts = od.CANCELED, ts, ts
                closed.append(o)
            else:
                self.order_manager.log.error(
                    f'cancel failed: order {o.id} may be already closed')
            self.order_manager.last_update_ts = now

        # remove closed(canceled) orders
        for o in closed:
            if o.side == od.BUY:
                self.buy.remove(o)
            elif o.side == od.SELL:
                self.sell.remove(o)
            else:
                assert False


class OrderManagerSimulator:
    def __init__(self, api, ws, retention=60, exchange=None):
        self.log = logging.getLogger(self.__class__.__name__)
        self.api = api
        self.ws = ws
        self.retention = retention  # retantion time of closed(canceled) order
        self.last_update_ts = 0
        self.orders = {}  # {id: Order}

        # simulator
        self.exchange = exchange
        self.simulator = {}  # {symbol: SymbolSimulator}
        self.quote_prec = None  # base_size-to-quote_size precision (bitmex=0)
        self.fee_func = self.default_fee_func

        name = self.exchange.__class__.__name__
        if name in ['Bitmex', 'Bybit']:
            self.quote_prec = 0
        elif name == 'Bitflyer':
            self.fee_func = bitflyer_fee_func

        run_forever_nonblocking(self.__worker, self.log, 1)

    def default_fee_func(self, symbol, side, price, amount, fee_rate):
        # price can be 0 if fee is not important
        if self.quote_prec is None:
            return price * amount * fee_rate, 0, None
        else:
            return amount * fee_rate, 0, None  # bitmex(SIZE_IN_QUOTE=True)

    def prepare_simulator(self, symbol):
        if symbol not in self.simulator:
            ex = self.exchange
            if symbol not in ex.trades:
                ex.create_trade(symbol)
            if symbol not in ex.orderbooks:
                ex.create_orderbook(symbol)
                ex.orderbooks[symbol].wait_initialized()

            self.simulator[symbol] = SymbolSimulator(
                self, self.api.ccxt_instance().market(symbol),
                ex.trades[symbol], ex.orderbooks[symbol])

        return self.simulator[symbol]

    def create_order(
            self, symbol, type_, side, amount, price=None, params={},
            event_cb=None, log=None, sync=False):
        o = None
        try:
            self.prepare_simulator(symbol)

            # check arguments
            assert type_ in [od.LIMIT, od.MARKET], 'invalid type'
            assert side in [od.BUY, od.SELL], 'invalid side'
            assert amount > 0, 'amount must be greater then 0'
            assert type_ != od.MARKET or price is None, 'price with market'
            assert type_ != od.LIMIT or price is not None, 'no price'

            o = od.Order(symbol, type_, side, amount, price, params)
            o.state, o.state_ts = od.WAIT_OPEN, time.time()
            o.event_cb = event_cb

            self.count_api('create_order')
            self.simulator[symbol].create_order(o)

            if sync:
                while o.state == od.WAIT_OPEN:
                    time.sleep(0.01)
                if not o.id:
                    raise Exception('create_order failed')
        finally:
            if log:
                opt = '(sync)' if sync else ''
                log.info(
                    f'create order{opt}: {symbol} {type_} {side} '
                    f'{amount} {price} {params} => {o and id(o)}')
        return o

    def cancel_order(self, o, log=None, sync=False):
        self.count_api('cancel_order')
        self.simulator[o.symbol].cancel_order(o)

        if o.state in [od.OPEN, od.WAIT_OPEN]:
            o.state, o.state_ts = od.WAIT_CANCEL, time.time()
        if sync:
            while o.state not in [od.CLOSED, od.CANCELED]:
                time.sleep(0.01)
        if log:
            opt = '(sync)' if sync else ''
            log.info(f'cancel order{opt}: {o.id}')

    def edit_order(self, o, amount, price, log=None, sync=False):
        self.count_api('edit_order')
        o.editing = True
        try:
            self.simulator[o.symbol].edit_order(o, amount, price)
        finally:
            o.editing = False
            if log:
                opt = '(sync)' if sync else ''
                log.info(
                    f'edit order{opt}: {o.symbol} {o.type_} {o.side} '
                    f'{o.amount} {o.price} {o.params} => {o and id(o)}')

    def count_api(self, path):
        if path in self.api.count:
            self.api.count[path] += 1
        else:
            self.api.count[path] = 1
        self.api.capacity -= 1

    def __worker(self):
        ts = time.time() - self.retention
        for id_ in [id_ for id_, o in self.orders.items()
                    if o.close_ts and ts > o.close_ts]:
            del self.orders[id_]
