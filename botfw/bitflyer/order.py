import time

from ..base.order import (
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CANCELED, WAIT_OPEN, WAIT_CANCEL,
    OrderManagerBase, OrderBase,
    OrderGroupManagerBase, OrderGroupBase,
    PositionGroupBase
)
from ..etc.util import unix_time_from_ISO8601Z

# silence linter (imported but unused)
_DUMMY = [
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CLOSED, CANCELED,
    WAIT_OPEN, WAIT_CANCEL
]

# Symbol
FX_BTC_JPY = 'FX_BTC_JPY'
BTC_JPY = 'BTC_JPY'
ETH_JPY = 'ETH_JPY'
# ETH_BTC = 'ETH_BTC'
# BCH_BTC = 'BCH_BTC'

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


class BitflyerOrder(OrderBase):
    def __init__(self, symbol, type_, side, amount, price=0,
                 minute_to_expire=43200, time_in_force=GTC):
        super().__init__(symbol, type_, side, amount, price)
        self.minute_to_expire = minute_to_expire
        self.time_in_force = time_in_force


class BitflyerOrderManager(OrderManagerBase):
    Order = BitflyerOrder

    def __init__(self, api, ws, external=True, retention=60):
        super().__init__(api, ws, external, retention)

    def _after_auth(self):
        self._init()
        self.ws.subscribe('child_order_events', self.__on_events)

    def _handle_events(self):
        if self._count_lock:
            return

        while self._event_queue:
            e = self._event_queue.popleft()
            o = self.__get_order(e)
            if not o:  # if order is not created by this class
                if e.event_type == EVENT_ORDER:
                    id_ = e.child_order_acceptance_id
                    o = self.Order(
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
                self._event_queue.append(e)

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
                self._old_orders.append(o)
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
            self._old_orders.append(o)
            self.log.warn(f'order failed: {id_} {e.reason}')
        elif t == EVENT_CANCEL:
            o.state, o.state_ts = CANCELED, now
            o.close_ts = ts
            self._old_orders.append(o)
        elif t == EVENT_CANCEL_FAILED:
            if o.state == WAIT_CANCEL:
                o.state, o.state_ts = OPEN, now
            self.log.warn(f'cancel failed: {id_}')
        elif t == EVENT_EXPIRE:
            o.state, o.state_ts = CANCELED, now
            self._old_orders.append(o)
            self.log.warn(f'order expired: {id_})')
        else:
            self.log.error(f'unknown event_type: {t}\n {id_}')

        if o.event_cb:
            o.event_cb(e)

    def __get_order(self, e):
        return self.orders.get(e.child_order_acceptance_id)


class BitflyerPositionGroup(PositionGroupBase):
    def __init__(self):
        super().__init__()
        self.sfd = 0  # total sfd
        self.commission = 0  # total commissions in jpy

    def _handle_event(self, e):
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


class BitflyerOrderGroup(OrderGroupBase):
    Order = BitflyerOrder
    PositionGroup = BitflyerPositionGroup

    def __init__(self, manager, name, symbol):
        super().__init__(manager, name, symbol)


class BitflyerOrderGroupManager(OrderGroupManagerBase):
    OrderGroup = BitflyerOrderGroup
    PositionGroup = BitflyerPositionGroup
    SYMBOLS = [FX_BTC_JPY, BTC_JPY, ETH_JPY]

    def __init__(self, order_manager, retention=60,
                 trades={}, position_sync_symbols=[]):
        super().__init__(order_manager, retention,
                         trades, position_sync_symbols)

    def _worker_destroy_order_group(self, og):
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
