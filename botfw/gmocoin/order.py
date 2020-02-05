from ..base import order as od
from .websocket import GmocoinWebsocketPrivate
from .api import GmocoinApi
from ..etc.util import unix_time_from_ISO8601Z


class GmocoinOrderManager(od.OrderManagerBase):
    WebsocketPrivate = GmocoinWebsocketPrivate

    def __init__(self, api, ws=None, retention=60):
        wspr = self.WebsocketPrivate(api)  # ws is unused
        super().__init__(api, wspr, retention)

    def _after_auth(self):
        self.ws.subscribe({'channel': 'executionEvents'}, self.__on_events)

    def _generate_order_object(self, e):
        info = e.info
        api = GmocoinApi.ccxt_instance()
        symbol = api.markets_by_id[info['symbol']]['symbol']
        return od.Order(
            symbol, info['executionType'].lower(), info['side'].lower(),
            float(info['orderExecutedSize']), float(info['orderPrice']))

    def __on_events(self, msg):
        e = msg
        oe = od.OrderEvent()
        oe.info = e
        oe.id = str(e['orderId'])
        oe.ts = unix_time_from_ISO8601Z(e['executionTimestamp'])
        oe.type = od.EVENT_EXECUTION
        oe.price = float(e['executionPrice'])
        size = float(e['executionSize'])
        oe.size = -size if e['side'] == 'SELL' else size
        self._handle_order_event(oe)


class GmocoinPositionGroup(od.PositionGroupBase):
    def __init__(self):
        super().__init__()
        # self.commission = 0  # total commissions in USD

    def update(self, price, size, info):
        super().update(price, size)
        # commission = info['commission'] * abs(size)
        # self.commission += commission
        # self.pnl -= commission


class GmocoinOrderGroup(od.OrderGroupBase):
    PositionGroup = GmocoinPositionGroup


class GmocoinOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = GmocoinOrderGroup
