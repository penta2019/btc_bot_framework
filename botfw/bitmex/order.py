from ..base import order as od
from .api import BitmexApi
from ..etc.util import unix_time_from_ISO8601Z


class BitmexOrderManager(od.OrderManagerBase):
    def __init__(self, api, ws=None, retention=60):
        super().__init__(api, ws, retention)
        self.ws.subscribe('execution', self.__on_events, True)

    def _generate_order_object(self, e):
        info = e.info
        api = BitmexApi.ccxt_instance()
        symbol = api.markets_by_id[info['symbol']]['symbol']
        return od.Order(
            symbol, info['ordType'].lower(), info['side'].lower(),
            info['orderQty'], info['price'])

    def __on_events(self, msg):
        if msg['action'] != 'insert':
            return

        for e in msg['data']:
            oe = od.OrderEvent()
            oe.info = e
            oe.id = e['orderID']
            oe.ts = unix_time_from_ISO8601Z(e['timestamp'])

            t = e['ordStatus']
            size = e['lastQty']
            if size:
                oe.type = od.EVENT_EXECUTION
                oe.price = e['lastPx']
                oe.size = -size if e['side'] == 'Sell' else size
                oe.fee = e['commission'] * size
            elif t == 'New':
                oe.type = od.EVENT_OPEN
            elif t == 'Filled':
                oe.type = od.EVENT_CLOSE
            elif t in ['Canceled', 'Rejected']:
                oe.type = od.EVENT_CANCEL

            self._handle_order_event(oe)


class BitmexPositionGroup(od.PositionGroupBase):
    SIZE_IN_QUOTE = True


class BitmexOrderGroup(od.OrderGroupBase):
    PositionGroup = BitmexPositionGroup


class BitmexOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BitmexOrderGroup
