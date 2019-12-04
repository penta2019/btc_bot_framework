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
XBT_USD = 'XBTUSD'

# EVENT_TYPE
EVENT_PARTIAL = 'partial'
EVENT_UPDATE = 'update'
EVENT_INSERT = 'insert'
EVENT_DELETE = 'delete'


class BitmexOrder(OrderBase):
    pass


class BitmexOrderManager(OrderManagerBase):
    Order = BitmexOrder

    def _after_auth(self):
        self._init()
        self.ws.subscribe('execution', self.__on_events)

    def _handle_events(self):
        if self._count_lock:
            return

        while self._event_queue:
            e = self._event_queue.popleft()
            o = self.__get_order(e)
            if not o:  # if order is not created by this class
                id_ = e.orderID
                o = BitmexOrder(
                    e.symbol, e.ordType, e.side, e.orderQty, e.price)
                o.id = id_
                o.external = True
                o.state, o.state_ts = WAIT_OPEN, time.time()
                self.orders[id_] = o
            self.__update_order(o, e)

    def __on_events(self, msg):
        if msg['action'] != 'insert':
            return

        for event in msg['data']:
            e = BitmexOrderEvent()
            e.__dict__ = event
            o = self.__get_order(e)
            if o:
                self.__update_order(o, e)
            else:
                # if event comes before create_order returns
                # or order is not created by this class
                self._event_queue.append(e)

    def __update_order(self, o, e):
        ts = unix_time_from_ISO8601Z(e.timestamp)
        now = time.time()

        status = e.ordStatus
        if status == 'New' and o.state != OPEN:
            o.open_ts = ts
            o.state, o.state_ts = OPEN, now
        elif status == 'Filled' and o.state != CLOSED:
            o.close_ts = ts
            o.state, o.state_ts = CLOSED, now
            self._old_orders.append(o)
        elif status == 'Canceled' and o.state != CANCELED:
            o.close_ts = ts
            o.state, o.state_ts = CANCELED, now
            self._old_orders.append(o)
        else:
            self.log.error(f'Unknown order status: {status}')

        filled = e.cumQty
        if filled != o.filled:
            o.trade_ts = ts
            o.filled = filled

        if o.event_cb:
            o.event_cb(e)

    def __get_order(self, e):
        return self.orders.get(e.orderID)


class BitmexPositionGroup(PositionGroupBase):
    SIZE_IN_FIAT = True

    def __init__(self):
        super().__init__()
        self.commission = 0  # total commissions in jpy

    def update(self, price, size, commission):
        super().update(price, size)
        self.commission += commission
        self.pnl -= commission


class BitmexOrderGroup(OrderGroupBase):
    Order = BitmexOrder
    PositionGroup = BitmexPositionGroup

    def _handle_event(self, e):
        p = e.lastPx
        s = e.lastQty
        c = e.commission

        if not p or not s:
            return

        s *= (1 if e.side.lower() == BUY else -1)
        self.position_group.update(p, s, c)


class BitmexOrderGroupManager(OrderGroupManagerBase):
    OrderGroup = BitmexOrderGroup
    PositionGroup = BitmexPositionGroup
    SYMBOLS = [XBT_USD]

    def __worker_destroy_order_group(self, og):
        pass  # TODO


class BitmexOrderEvent:
    pass

    # [table='execution' action='insert']       [Used fields]
    # 'account': 0
    # 'avgPx': None
    # 'clOrdID': ''
    # 'clOrdLinkID': ''
    # 'commission': None
    # 'contingencyType': ''
    # 'cumQty': 0                                # filled
    # 'currency': 'USD'
    # 'displayQty': None
    # 'exDestination': 'XBME'
    # 'execComm': None
    # 'execCost': None
    # 'execID': '***********************'
    # 'execInst': 'ParticipateDoNotInitiate'
    # 'execType': 'Canceled'                     # event type
    # 'foreignNotional': None
    # 'homeNotional': None
    # 'lastLiquidityInd': ''
    # 'lastMkt': ''
    # 'lastPx': None                             # execution price
    # 'lastQty': None                            # execution size
    # 'leavesQty': 0
    # 'multiLegReportingType': 'SingleSecurity'
    # 'ordRejReason': ''
    # 'ordStatus': 'Canceled'                    # state
    # 'ordType': 'Limit'                         # type
    # 'orderID': '**************************'    # id
    # 'orderQty': 1                              # size (USD)
    # 'pegOffsetValue': None
    # 'pegPriceType': ''
    # 'price': 7105                              # price
    # 'settlCurrency': 'XBt'
    # 'side': 'Sell'                             # side
    # 'simpleCumQty': None
    # 'simpleLeavesQty': None
    # 'simpleOrderQty': None
    # 'stopPx': None
    # 'symbol': 'XBTUSD'
    # 'text': 'Canceled: Order had execInst of ParticipateDoNotInitiate\n'
    #         'Submission from www.bitmex.com'
    # 'timeInForce': 'GoodTillCancel'            # time in force
    # 'timestamp': '2019-12-02T15:53:01.634Z'    # timestamp
    # 'tradePublishIndicator': ''
    # 'transactTime': '2019-12-02T15:53:01.634Z'
    # 'trdMatchID': '00000000-0000-0000-0000-000000000000'
    # 'triggered': ''
    # 'underlyingLastPx': None
    # 'workingIndicator': False
