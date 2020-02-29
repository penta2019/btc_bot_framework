import time

from ..base import order as od
from .api import BybitApi


class BybitOrderManager(od.OrderManagerBase):
    def __init__(self, api, ws=None, retention=60):
        super().__init__(api, ws, retention)
        self.ws.subscribe('execution', self.__on_events, True)
        self.ws.subscribe('position', self.__on_events, True)
        self.ws.subscribe('order', self.__on_events, True)

    def _generate_order_object(self, e):
        info = e.info
        if e.type != od.EVENT_OPEN:
            self.log.warning(f'event for unknown order: {e}')
            return None

        api = BybitApi.ccxt_instance()
        symbol = api.markets_by_id[info['symbol']]['symbol']
        return od.Order(
            symbol, info['order_type'].lower(), info['side'].lower(),
            info['qty'], float(info['price']))

    def __on_events(self, msg):
        topic = msg['topic']

        for e in msg['data']:
            oe = od.OrderEvent()
            oe.info = e
            oe.ts = time.time()
            if topic == 'order':
                oe.id = e['order_id']
                st = e['order_status']
                if st == 'New':
                    oe.type = od.EVENT_OPEN
                elif st == 'Filled':
                    oe.type = od.EVENT_CLOSE
                elif st in ['Cancelled', 'Rejected']:
                    oe.type = od.EVENT_CANCEL
                else:  # ignore(PartiallyFilled, Created, PendingCancel)
                    continue
            elif topic == 'execution':
                oe.type = od.EVENT_EXECUTION
                oe.id = e['order_id']
                oe.price = float(e['price'])
                size = e['exec_qty']
                oe.size = -size if e['side'] == 'Sell' else size
                oe.fee = float(e['exec_fee']) * size
            elif topic == 'position':
                break
            else:
                assert False

            self._handle_order_event(oe)


class BybitPositionGroup(od.PositionGroupBase):
    SIZE_IN_QUOTE = True


class BybitOrderGroup(od.OrderGroupBase):
    PositionGroup = BybitPositionGroup


class BybitOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BybitOrderGroup
