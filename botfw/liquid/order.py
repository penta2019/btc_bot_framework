from ..base import order as od
from .api import LiquidApi
from ..etc.util import unix_time_from_ISO8601Z, decimal_add


class LiquidOrderManager(od.OrderManagerBase):
    SYMBOLS = ['BTC/JPY', 'ETH/JPY', 'XRP/JPY']

    def _after_auth(self):
        for symbol in self.SYMBOLS:
            s = symbol.replace('/', '').lower()
            self.ws.subscribe(f'user_executions_cash_{s}', self.__on_events)

    def _generate_order_object(self, e):
        print('_generate_order_object', e)

    def __on_events(self, msg):
        print('__on_events', msg)
        # self._handle_order_event(oe)


class LiquidPositionGroup(od.PositionGroupBase):
    pass


class LiquidOrderGroup(od.OrderGroupBase):
    PositionGroup = LiquidPositionGroup


class LiquidOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = LiquidOrderGroup
