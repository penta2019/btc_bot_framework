from ..base import order as od
from .api import ccxt_bitflyer
from ..etc.util import unix_time_from_ISO8601Z, decimal_add


class BitflyerOrderManager(od.OrderManagerBase):
    def _after_auth(self):
        self.ws.subscribe('child_order_events', self.__on_events)

    def _generate_order_object(self, e):
        info = e.info
        if info['event_type'] != 'ORDER':
            self.log.warning(f'event for unknown order: {info}')
            return None

        symbol = ccxt_bitflyer.markets_by_id[info['product_code']]['symbol']
        return od.Order(
            symbol, info['child_order_type'].lower(), info['side'].lower(),
            info['size'], info['price'])

    def __on_events(self, msg):
        for e in msg['params']['message']:
            oe = od.OrderEvent()
            oe.info = e
            oe.id = e['child_order_acceptance_id']
            oe.ts = unix_time_from_ISO8601Z(e['event_date'])

            t = e['event_type']
            if t == 'EXECUTION':
                oe.type = od.EVENT_EXECUTION
                oe.price = e['price']
                oe.size = e['size'] if e['side'] == 'BUY' else -e['size']
            elif t == 'ORDER':
                oe.type = od.EVENT_OPEN
            elif t in ['CANCEL', 'EXPIRE']:
                oe.type = od.EVENT_CANCEL
            elif t == 'ORDER_FAILED':
                oe.type = od.EVENT_OPEN_FAILED
                oe.message = e['reason']
            elif t == 'CANCEL_FAILED':
                oe.type = od.EVENT_CANCEL_FAILED

            self._handle_order_event(oe)


class BitflyerPositionGroup(od.PositionGroupBase):
    def __init__(self):
        super().__init__()
        self.sfd = 0  # total sfd
        self.commission = 0  # total commissions in JPY

    def update(self, price, size, info):
        super().update(price, size)
        commission, sfd = info['commission'], info['sfd']
        self.position = decimal_add(self.position, -commission)
        c = price * commission
        self.commission += c
        self.sfd += sfd
        self.pnl += -c + sfd


class BitflyerOrderGroup(od.OrderGroupBase):
    PositionGroup = BitflyerPositionGroup


class BitflyerOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BitflyerOrderGroup
