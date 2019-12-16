import time

from ..base.order import (
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CANCELED, WAIT_OPEN, WAIT_CANCEL,
    OrderManagerBase, OrderBase,
    OrderGroupManagerBase, OrderGroupBase,
    PositionGroupBase
)
from .api import ccxt_bitflyer
from ..etc.util import unix_time_from_ISO8601Z, decimal_sum

# silence linter (imported but unused)
_DUMMY = [
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CANCELED,
    WAIT_OPEN, WAIT_CANCEL
]


class BitflyerOrder(OrderBase):
    pass


class BitflyerOrderManager(OrderManagerBase):
    Order = BitflyerOrder

    def _after_auth(self):
        self.ws.subscribe('child_order_events', self.__on_events)

    def _get_order_id(self, e):
        return e.child_order_acceptance_id

    def _update_order(self, o, e):
        t = e.event_type
        id_ = e.child_order_acceptance_id
        ts = unix_time_from_ISO8601Z(e.event_date)
        now = time.time()
        if t == 'EXECUTION':
            o.filled = decimal_sum(o.filled + e.size)
            if o.filled == o.amount:
                o.state, o.state_ts = CLOSED, now
                o.close_ts = ts
            elif o.state != OPEN:
                o.state, o.state_ts = OPEN, now
                self.log.warn('something wrong with order state handling')
        elif t == 'ORDER':
            o.open_ts = ts
            o.child_order_id = e.child_order_id
            if o.state == WAIT_OPEN:
                o.state, o.state_ts = OPEN, now
        elif t == 'CANCEL_FAILED':
            if o.state == WAIT_CANCEL:
                o.state, o.state_ts = OPEN, now
            self.log.warn(f'cancel failed: {id_}')
        elif t in ['CANCEL', 'ORDER_FAILED', 'EXPIRE']:
            o.state, o.state_ts = CANCELED, now
            o.close_ts = ts
            if t == 'ORDER_FAILED':
                self.log.warn(f'order failed: {id_} {e.reason}')
            elif t == 'EXPIRE':
                self.log.warn(f'order expired: {id_})')
        else:
            self.log.error(f'unknown event_type: {t}\n {id_}')

    def _create_external_order(self, e):
        if e.event_type != 'ORDER':
            self.log.warn(f'event for unknown order: {e.__dict__}')
            return None

        symbol = ccxt_bitflyer.markets_by_id[e.product_code]['symbol']
        return self.Order(
            symbol, e.child_order_type.lower(),
            e.side.lower(), e.size, e.price)

    def __on_events(self, msg):
        for event in msg['params']['message']:
            e = BitflyerOrderEvent()
            e.__dict__ = event
            self._handle_order_event(e)


class BitflyerPositionGroup(PositionGroupBase):
    def __init__(self):
        super().__init__()
        self.sfd = 0  # total sfd
        self.commission = 0  # total commissions in JPY

    def update(self, price, size, commission, sfd):
        super().update(price, size)
        self.position = decimal_sum(self.position, -commission)
        c = price * commission
        self.commission += c
        self.sfd += sfd
        self.pnl += -c + sfd


class BitflyerOrderGroup(OrderGroupBase):
    PositionGroup = BitflyerPositionGroup

    def _handle_event(self, e):
        if e.event_type != 'EXECUTION':
            return

        size = e.size if e.side.lower() == BUY else -e.size
        self.position_group.update(e.price, size, e.commission, e.sfd)


class BitflyerOrderGroupManager(OrderGroupManagerBase):
    OrderGroup = BitflyerOrderGroup


class BitflyerOrderEvent:
    pass
    # https://bf-lightning-api.readme.io/docs/realtime-child-order-events
