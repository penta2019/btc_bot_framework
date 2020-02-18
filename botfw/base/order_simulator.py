import time
import logging

from sortedcontainers import SortedList

from ..etc.util import decimal_add, run_forever_nonblocking
from . import order as od


def event_open(id_, ts):
    oe = od.OrderEvent()
    oe.type = od.EVENT_OPEN
    oe.id = id_
    oe.ts = ts
    return oe


def event_execution(id_, ts, price, size, fee):
    oe = od.OrderEvent()
    oe.type = od.EVENT_EXECUTION
    oe.id = id_
    oe.ts = ts
    oe.price = price
    oe.size = size
    oe.fee = fee
    return oe


class SimulationInfo(dict):
    def __init__(self):
        super().__init__()
        self.__dict__ = self
        self.buy = SortedList(key=lambda o: -o.price)
        self.sell = SortedList(key=lambda o: o.price)
        self.pending = []      # [order]
        self.canceling = []    # [order]
        self.taker_fee = 0
        self.maker_fee = 0


class OrderManagerSimulator:
    def __init__(self, api, ws, retention=60):
        self.log = logging.getLogger(self.__class__.__name__)
        self.api = api
        self.ws = ws
        self.retention = retention  # retantion time of closed(canceled) order
        self.last_update_ts = 0
        self.orders = {}  # {id: Order}

        # simulator
        self.simulation_info = {}  # {symbol: SimulationInfo}
        self.exchange = None
        self.delay_create_order = 0.1
        self.delay_cancel_order = 0.1
        self.quote_prec = None  # size precision in quote. bitmex = 0
        run_forever_nonblocking(self.__worker, self.log, 1)

    def prepare_simulation(self, symbol):
        if symbol in self.simulation_info:
            return

        market = self.api.ccxt_instance().market(symbol)

        ex = self.exchange
        if symbol not in ex.trades:
            ex.create_trade(symbol)
        if symbol not in ex.orderbooks:
            ex.create_orderbook(symbol)
            ex.wait_initialized()

        ex.trades[symbol].add_callback(
            lambda ts, price, size: self.trade_callback(
                symbol, ts, price, size))

        sd = SimulationInfo()
        sd.taker_fee = market['taker']
        sd.maker_fee = market['maker']
        self.simulation_info[symbol] = sd

    def create_order(
            self, symbol, type_, side, amount, price=None, params={},
            event_cb=None, log=None, sync=False):
        # check arguments
        assert type_ in [od.LIMIT, od.MARKET], 'invalid type'
        assert side in [od.BUY, od.SELL], 'invalid side'
        assert type_ != od.MARKET or price is None, 'price with market'
        assert type_ != od.LIMIT or price is not None, 'no price with limit'

        self.prepare_simulation(symbol)

        o = od.Order(symbol, type_, side, amount, price, params)
        o.state, o.state_ts = od.WAIT_OPEN, time.time()
        o.event_cb = event_cb

        self.simulation_info[symbol].pending.append(o)

        if sync:
            while o.state == od.WAIT_OPEN:
                time.sleep(0.01)
            if not o.id:
                raise Exception('create_order failed')
        if log:
            opt = '(sync)' if sync else ''
            log.info(
                f'create order{opt}: {o.symbol} {o.type} {o.side} '
                f'{o.amount} {o.price} {o.params} => {id(o)}')
        return o

    def cancel_order(self, o, log=None, sync=False):
        self.simulation_info[o.symbol].canceling.append(o)
        if o.state in [od.OPEN, od.WAIT_OPEN]:
            o.state, o.state_ts = od.WAIT_CANCEL, time.time()
        if sync:
            time.sleep(self.delay_cancel_order)
        if log:
            opt = '(sync)' if sync else ''
            log.info(f'cancel order{opt}: {o.id}')

    def execute(self, o, ts, price, max_size, fee_rate):
        remaining = decimal_add(o.amount, -o.filled)
        executed = min(remaining, max_size)
        o.filled = decimal_add(o.filled, executed)
        if o.amount == o.filled:
            o.state, o.state_ts = od.CLOSED, ts
            o.close_ts = ts
        if o.event_cb:
            size = -executed if o.side == od.SELL else executed
            fee = executed * fee_rate
            if self.quote_prec is None:
                fee *= price
            o.event_cb(event_execution(o.id, ts, price, size, fee))
        return executed

    def trade_callback(self, symbol, ts, price, size):
        d = self.simulation_info[symbol]
        qp = self.quote_prec
        size = size if qp is None else round(price * size, qp)
        closed = []

        # handle pending orders
        ts0 = ts - self.delay_create_order
        for o in [o for o in d.pending if ts0 > o.state_ts]:
            o.id = id(o)
            o.state, o.state_ts = od.OPEN, ts
            self.orders[o.id] = o
            d.pending.remove(o)

            if o.event_cb:
                o.event_cb(event_open(o.id, ts))

            # simulate take execution
            worst_price = price
            if o.side == od.BUY:
                for p, s in self.exchange.orderbooks[symbol].asks():
                    if (o.price and p >= o.price) or o.amount == o.filled:
                        break
                    s = s if qp is None else round(p * s, qp)
                    self.execute(o, ts, p, s, d.taker_fee)
                    worst_price = p
            elif o.side == od.SELL:
                for p, s in self.exchange.orderbooks[symbol].bids():
                    if (o.price and p <= o.price) or o.amount == o.filled:
                        break
                    s = s if qp is None else round(p * s, qp)
                    self.execute(o, ts, p, s, d.taker_fee)
                    worst_price = p
            else:
                assert False

            if o.amount != o.filled:  # order is remaining
                if o.price:  # limit
                    if o.side == od.BUY:
                        d.buy.add(o)
                    elif o.side == od.SELL:
                        d.sell.add(o)
                    else:
                        assert False
                else:  # market
                    # when amount is big enough to take all orders on orderbook
                    self.execute(o, ts, worst_price, o.amount, d.taker_fee)

        # simulate make execution
        if size < 0:  # buy(taker=sell)
            remaining = -size
            for o in d.buy:
                if o.price <= price or remaining == 0:
                    break
                executed = self.execute(o, ts, o.price, remaining, d.maker_fee)
                remaining = decimal_add(remaining, -executed)
                if o.state == od.CLOSED:
                    closed.append(o)
        else:  # sell(taker=BUY)
            remaining = size
            for o in d.sell:
                if o.price >= price or remaining == 0:
                    break
                executed = self.execute(o, ts, o.price, remaining, d.maker_fee)
                remaining = decimal_add(remaining, -executed)
                if o.state == od.CLOSED:
                    closed.append(o)

        # handle canceling orders
        ts0 = ts - self.delay_cancel_order
        for o in [o for o in d.canceling if ts0 > o.state_ts]:
            d.canceling.remove(o)
            if o.state != od.CLOSED:
                o.state, o.close_ts = od.CANCELED, ts
                if o.side == od.BUY:
                    closed.append(o)
                elif o.side == od.SELL:
                    closed.append(o)
                else:
                    assert False

        # remove closed(canceled) orders
        for o in closed:
            if o.side == od.BUY:
                d.buy.remove(o)
            elif o.side == od.SELL:
                d.sell.remove(o)
            else:
                assert False

    def __worker(self):
        ts = time.time() - self.retention
        for id_ in [id_ for id_, o in self.orders.items()
                    if o.close_ts and ts > o.close_ts]:
            del self.orders[id_]


class OrderGroupManagerSimulator(od.OrderGroupManagerBase):
    def __init__(self, *arg):
        super().__init__(*arg)
        self.order_group_class = self.OrderGroup

    def create_order_group(self, symbol, name):
        if name in self.order_groups:
            self.log.error('Failed to create order group. '
                           f'Order group "{name}" already exists.')
            return None

        og = self.order_group_class(self, symbol, name)
        self.order_groups[name] = og
        og.log.info('created')
        return og

    def set_position_sync_config(self, *args):
        self.log.warning(
            'set_position_sync_config is ignored in emulator mode.')

    def __worker__(self):
        self.__update_unrealized_pnl()
