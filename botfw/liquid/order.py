import json
import logging

from ..base import order as od
from .api import LiquidApi


class LiquidOrderManager(od.OrderManagerBase):
    SYMBOLS = ['BTC/JPY', 'ETH/JPY', 'XRP/JPY']

    def __init__(self, api, ws=None, retention=60):
        super().__init__(api, ws, retention)
        for symbol in self.SYMBOLS:
            s = symbol.replace('/', '').lower()
            self.ws.subscribe(f'user_executions_cash_{s}', self.__on_events)
        self.ws.subscribe(f'user_account_jpy_orders', self.__on_events)
        self.ws.subscribe(f'user_account_jpy_trades', self.__on_events)

    def _generate_order_object(self, e):
        info = e.info
        if e.type != od.EVENT_OPEN:
            self.log.warning(f'event for unknown order: {e}')
            return None

        api = LiquidApi.ccxt_instance()
        symbol = api.markets_by_id[info['product_id']]['symbol']
        o = od.Order(
            symbol, info['order_type'], info['side'],
            info['quantity'], info['price'])
        o.filled = info['filled_quantity']
        return o

    def __on_events(self, msg):
        e = json.loads(msg['data'])
        oe = od.OrderEvent()
        oe.info = e
        ch = msg['channel']
        if '_orders' in ch:
            oe.id = str(e['id'])
            st = e['status']
            oe.ts = e['updated_at']
            if st == 'live':
                oe.type = od.EVENT_OPEN
            elif st == 'filled':
                oe.type = od.EVENT_CLOSE
            elif st == 'cancelled':
                oe.type = od.EVENT_CANCEL
        elif '_trades' in ch:
            return  # ignore
        elif 'user_executions_cash_' in ch:
            oe.type = od.EVENT_EXECUTION
            oe.id = str(e['order_id'])
            oe.ts = e['created_at']
            oe.price = e['price']
            size = e['quantity']
            oe.size = -size if e['my_side'] == 'sell' else size
            oe.fee = 0

        self._handle_order_event(oe)


class LiquidPositionGroup(od.PositionGroupBase):
    pass


class LiquidOrderGroup(od.OrderGroupBase):
    PositionGroup = LiquidPositionGroup

    def __init__(self, manager, symbol, name):
        super().__init__(manager, symbol, name)
        self.leverage = 4

    def create_order(
            self, type_, side, amount, price=None, params={}, sync=False):
        if self.leverage == 1:
            params['leverage_level'] = 1
        else:
            params['leverage_level'] = self.leverage
            params['order_direction'] = 'netout'

        return super().create_order(type_, side, amount, price, params, sync)


class LiquidOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = LiquidOrderGroup

    def create_order_group(self, symbol, name, leverage=4):
        if name in self.order_groups:
            self.log.error('Failed to create order group. '
                           f'Order group "{name}" already exists.')
            return None

        og = self.OrderGroup(self, symbol, name)
        og.leverage = leverage
        og.log = logging.getLogger(
            f'{self.__class__.__name__}({name}@{symbol}x{leverage})')
        self.order_groups[name] = og
        og.log.info('created')
        return og
