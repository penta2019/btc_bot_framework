import time

from ..base import order as od
from .api import ccxt_bitflyer
from ..etc.util import unix_time_from_ISO8601Z, decimal_sum


class BitflyerOrder(od.OrderBase):
    pass


class BitflyerOrderManager(od.OrderManagerBase):
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
            o.filled = decimal_sum(o.filled, e.size)
            if o.filled == o.amount:
                o.state, o.state_ts = od.CLOSED, now
                o.close_ts = ts
            elif o.state != od.OPEN:
                o.state, o.state_ts = od.OPEN, now
                self.log.warning('got an execution for a not "open" order')
        elif t == 'ORDER':
            o.open_ts = ts
            o.child_order_id = e.child_order_id
            if o.state == od.WAIT_OPEN:
                o.state, o.state_ts = od.OPEN, now
        elif t == 'CANCEL_FAILED':
            if o.state == od.WAIT_CANCEL:
                o.state, o.state_ts = od.OPEN, now
            self.log.warning(f'cancel failed: {id_}')
        elif t in ['CANCEL', 'ORDER_FAILED', 'EXPIRE']:
            o.state, o.state_ts = od.CANCELED, now
            o.close_ts = ts
            if t == 'ORDER_FAILED':
                self.log.warning(f'order failed: {id_} {e.reason}')
            elif t == 'EXPIRE':
                self.log.warning(f'order expired: {id_})')
        else:
            self.log.error(f'unknown event_type: {t}\n {id_}')

    def _generate_order_object(self, e):
        if e.event_type != 'ORDER':
            self.log.warning(f'event for unknown order: {e.__dict__}')
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


class BitflyerPositionGroup(od.PositionGroupBase):
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


class BitflyerOrderGroup(od.OrderGroupBase):
    PositionGroup = BitflyerPositionGroup

    def _handle_event(self, e):
        if e.event_type != 'EXECUTION':
            return

        size = e.size if e.side.lower() == od.BUY else -e.size
        self.position_group.update(e.price, size, e.commission, e.sfd)


class BitflyerOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BitflyerOrderGroup


class BitflyerOrderEvent:
    pass
    # https://bf-lightning-api.readme.io/docs/realtime-child-order-events
