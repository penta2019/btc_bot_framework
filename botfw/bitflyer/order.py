import time
import logging
import collections
import threading

from ..base.order import (
    OrderManagerBase, OrderBase,
    OrderGroupManagerBase, OrderGroupBase,
    PositionGroupBase
)
from ..etc.util import run_forever_nonblocking, unix_time_from_ISO8601Z

# Order Side
BUY = 'buy'
SELL = 'sell'

# Order Type
LIMIT = 'limit'
MARKET = 'market'

# Order state
OPEN = 'open'
CLOSED = 'closed'
CANCELED = 'canceled'
WAIT_OPEN = 'wait_open'
WAIT_CANCEL = 'wait_cancel'

# Symbol
FX_BTC_JPY = 'FX_BTC_JPY'
BTC_JPY = 'BTC_JPY'
ETH_JPY = 'ETH_JPY'
# ETH_BTC = 'ETH_BTC'
# BCH_BTC = 'BCH_BTC'
SYMBOLS = [FX_BTC_JPY, BTC_JPY, ETH_JPY]

# Time in force
GTC = 'GTC'
FOK = 'FOK'
IOC = 'IOC'

# Event Type
EVENT_ORDER = 'ORDER'
EVENT_ORDER_FAILED = 'ORDER_FAILED'
EVENT_CANCEL = 'CANCEL'
EVENT_CANCEL_FAILED = 'CANCEL_FAILED'
EVENT_EXECUTION = 'EXECUTION'
EVENT_EXPIRE = 'EXPIRE'


class BitflyerOrderEvent:
    pass

    # https://bf-lightning-api.readme.io/docs/realtime-child-order-events
    # [Property]       [Type] [Description]
    # product_code     String BTC_JPY,FX_BTC_JPY, etc.
    # child_order_id   String order id(never used)
    # child_order_acc~ String child_order_acceptance_id(=id)
    # event_date       String Event occurrence time
    # event_type       String ORDER, ORDER_FAILED, CANCEL,
    #                         CANCEL_FAILED, EXECUTION, EXPIRE
    # child_order_type String LIMIT, MARKET (ORDER)
    # expire_date      String Order deadline (ORDER, EXECUTION)
    # reason           String Reason why order was rejected (ORDER_FAILED)
    # exec_id          Number execution id (EXECUTION)
    # side             String SELL, BUY (ORDER, EXECUTION)
    # price            Number price (ORDER, EXECUTION)
    # size             Number amount (ORDER, EXECUTION)
    # commission       Number Order execution fee (EXECUTION)
    # sfd              Number swap for difference (EXECUTION)


class BitflyerOrderManager(OrderManagerBase):
    def __init__(self, api, ws, external=True, retention=60):
        super().__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self.api = api  # BitflyerApi
        self.ws = ws  # BitflyerWs (with auth)
        self.ws.add_after_auth_callback(self.__after_auth)
        self.external = external  # True to allow external orders
        self.retention = retention  # retantion time of closed(canceled) order
        self.orders = {}  # {id: BitflyerOrderInfo}
        self.__count_lock = 0
        self.__event_queue = collections.deque()
        self.__old_orders = collections.deque()

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order(self, symbol, type_, side, amount, price=0,
                     minute_to_expire=43200, time_in_force=GTC):
        o = BitflyerOrder(symbol, type_, side, amount, price,
                          minute_to_expire, time_in_force)
        return self.create_order_internal(o)

    def create_order_internal(self, o):
        try:
            self.__count_lock += 1

            res = self.api.create_order(
                o.symbol, o.type, o.side, o.amount, o.price,
                o.minute_to_expire, o.time_in_force)
            o.id = res['id']
            o.state, o.state_ts = WAIT_OPEN, time.time()
            self.orders[o.id] = o
        finally:
            self.__count_lock -= 1

        return o

    def cancel_order(self, o):
        self.api.cancel_order(o.id, o.symbol)
        o.state = WAIT_CANCEL
        o.state_ts = time.time()

    def __after_auth(self):
        self.orders = {}
        self.__event_queue = collections.deque()
        self.__old_orders = collections.deque()
        self.ws.subscribe('child_order_events', self.__on_events)

    def __on_events(self, msg):
        for event in msg['params']['message']:
            e = BitflyerOrderEvent()
            e.__dict__ = event
            o = self.__get_order(e)
            if o:
                self.__update_order(o, e)
            else:
                # if event comes before create_order returns
                # or order is not created by this class
                self.__event_queue.append(e)

    def __handle_events(self):
        if self.__count_lock:
            return

        while self.__event_queue:
            e = self.__event_queue.popleft()
            o = self.__get_order(e)
            if not o:  # if order is not created by this class
                if e.event_type == EVENT_ORDER:
                    id_ = e.child_order_acceptance_id
                    o = BitflyerOrder(
                        e.product_code, e.child_order_type,
                        e.side, e.size, e.price)
                    o.id = id_
                    o.external = True
                    o.state, o.state_ts = WAIT_OPEN, time.time()
                    self.orders[id_] = o
                else:
                    self.log.warn(f'event for unknown order: {e.__dict__}')
                    continue
            self.__update_order(o, e)

    def __update_order(self, o, e):
        t = e.event_type
        id_ = e.child_order_acceptance_id
        ts = unix_time_from_ISO8601Z(e.event_date)
        now = time.time()
        if t == EVENT_EXECUTION:
            o.filled = round(o.filled + e.size, 8)
            if o.filled == o.amount:
                o.state, o.state_ts = CLOSED, now
                o.close_ts = ts
                self.__old_orders.append(o)
            elif o.state != OPEN:
                o.state, o.state_ts = OPEN, now
                self.log.warn('something wrong with order state handling')
        elif t == EVENT_ORDER:
            o.open_ts = ts
            o.child_order_id = e.child_order_id
            if o.state == WAIT_OPEN:
                o.state, o.state_ts = OPEN, now
        elif t == EVENT_ORDER_FAILED:
            o.state, o.state_ts = CANCELED, now
            self.__old_orders.append(o)
            self.log.warn(f'order failed: {id_} {e.reason}')
        elif t == EVENT_CANCEL:
            o.state, o.state_ts = CANCELED, now
            o.close_ts = ts
            self.__old_orders.append(o)
        elif t == EVENT_CANCEL_FAILED:
            if o.state == WAIT_CANCEL:
                o.state, o.state_ts = OPEN, now
            self.log.warn(f'cancel failed: {id_}')
        elif t == EVENT_EXPIRE:
            o.state, o.state_ts = CANCELED, now
            self.__old_orders.append(o)
            self.log.warn(f'order expired: {id_})')
        else:
            self.log.error(f'unknown event_type: {t}\n {id_}')

        if o.event_cb:
            o.event_cb(e)

    def __get_order(self, e):
        return self.orders.get(e.child_order_acceptance_id)

    def __remove_old_order(self):
        while self.__old_orders:
            o = self.__old_orders[0]
            if time.time() - o.state_ts > self.retention:
                self.__old_orders.popleft()
                self.orders.pop(o.id, None)
            else:
                break

    def __cancel_external_orders(self):
        for o in self.orders.values():
            if o.external and o.state == OPEN:
                self.log.warn(
                    f'cancel external order: {o.id}')
                self.cancel_order(o)

    def __worker(self):
        self.__handle_events()
        self.__remove_old_order()
        if not self.external:
            self.__cancel_external_orders()


class BitflyerOrder(OrderBase):
    def __init__(self, symbol, type_, side, amount, price=0,
                 minute_to_expire=43200, time_in_force=GTC):
        super().__init__(symbol, type_, side, amount, price)
        self.minute_to_expire = minute_to_expire
        self.time_in_force = time_in_force


class BitflyerOrderGroupManager(OrderGroupManagerBase):
    def __init__(self, order_manager, trades={},
                 position_sync_symbols=[], retention=60):
        super().__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self.order_manager = order_manager
        self.order_groups = {}
        self.position_sync_symbols = position_sync_symbols  # TODO
        self.trades = trades  # {symbol:Trade}, used to update unrealized pnl
        self.retention = retention

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order_group(self, name, symbol):
        if name in self.order_groups:
            self.log.error('Failed to create order group. '
                           f'Order group "{name}" already exists.')
            return None

        og = BitflyerOrderGroup(self, name, symbol)
        self.order_groups[name] = og
        return og

    def destroy_order_group(self, og, clean=True):
        name = og.name
        if name not in self.order_groups:
            self.log.error('Failed to destroy order group. '
                           f'Unknown order group "{name}". ')

        og = self.order_groups.pop(name)
        og.clean = clean  # whether to clean OrderGroup position

        thread = threading.Thread(
            name=f'clean_{og.name}', target=self.__worker_destroy_order_group,
            args=[og])
        thread.daemon = True
        thread.start()

    def get_total_positions(self):
        positions = {}
        for s in SYMBOLS:
            positions[s] = BitflyerPositionGroup()

        for og in self.order_groups.values():
            p0, p = positions[og.symbol], og.position
            for k in p:
                p0[k] += p[k]

        return positions

    def __worker(self):
        # remove closed orders older than retention time
        if self.retention is not None:
            for og in self.order_groups.values():
                og.remove_closed_orders(self.retention)

        # update unrealized pnl if possible
        for og in self.order_groups.values():
            t = self.trades.get(og.symbol)
            if t and t.ltp:
                og.position_group.update_unrealized_pnl(t.ltp)

    def __worker_destroy_order_group(self, og):
        while True:
            # cancel remaining orders except for position cleaning orders
            is_remain = False
            for o in og.orders.values():
                if o.state in [OPEN, WAIT_OPEN]:
                    og.cancel_order(o)
                    is_remain = True

            if is_remain:
                time.sleep(3)
                continue

            # clean position if needed
            pos = og.position.pos
            if abs(pos) < 0.01:
                og.create_order(MARKET, BUY, 0.02)
                pos = round(pos + 0.02, 8)

            lot = 0.5
            while abs(pos) >= 0.01:
                if lot < pos:
                    size = -lot
                elif 0 < pos < lot:
                    size = -pos
                elif -lot < pos < 0:
                    size = pos
                else:  # pos <= lot
                    size = lot
                pos = round(pos + size, 8)

                if size > 0:
                    side, size = BUY, size
                else:
                    side, size = SELL, -size
                self.log.info(
                    f'{og.symbol} {side} {MARKET} {size} ({og.name} clean)')
                og.create_order(MARKET, side, size)
                time.sleep(1)

            if not og.clean or og.position.pos == 0:
                self.log.info(
                    f'Destroyed order group "{og.name}" successfully.')
                break


class BitflyerOrderGroup(OrderGroupBase):
    def __init__(self, manager, name, symbol):
        super().__init__()
        self.name = name
        self.symbol = symbol
        self.manager = manager
        self.position_group = BitflyerPositionGroup()
        self.orders = {}

    def create_order(self, type_, side, amount, price=0,
                     minute_to_expire=43200, time_in_force=GTC):
        o = BitflyerOrder(self.symbol, type_, side, amount, price,
                          minute_to_expire, time_in_force)
        o.event_cb = self.position_group.handle_event
        o.group_name = self.name
        o = self.manager.order_manager.create_order_internal(o)
        self.orders[o.id] = o
        return o

    def cancel_order(self, o):
        self.manager.order_manager.cancel_order(o)

    def remove_closed_orders(self, retention=0):
        now = time.time()
        for id_, o in self.orders.items():
            if o.state in [CLOSED, CANCELED]:
                if o.state_ts - now > retention:
                    del self.orders[id_]


class BitflyerPositionGroup(PositionGroupBase):
    def __init__(self):
        super().__init__()
        self.sfd = 0  # total sfd
        self.commission = 0  # total commissions in jpy

    def handle_event(self, e):
        if e.event_type != EVENT_EXECUTION:
            return

        p = e.price
        s = e.size * (1 if e.side == BUY else -1)
        c = e.commission
        sfd = e.sfd

        self.update(p, s)
        self.position = round(self.position - c, 8)
        self.sfd += sfd
        self.commission += p * c
        self.pnl += -p * c + sfd
