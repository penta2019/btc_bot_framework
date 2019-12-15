import time

from ..base.order import (
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CANCELED, WAIT_OPEN, WAIT_CANCEL,
    OrderManagerBase, OrderBase,
    OrderGroupManagerBase, OrderGroupBase,
    PositionGroupBase
)
from .websocket_user_data import BinanceWebsocketUserData
from .api import ccxt_binance

# silence linter (imported but unused)
_DUMMY = [
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CANCELED,
    WAIT_OPEN, WAIT_CANCEL
]


class BinanceOrder(OrderBase):
    pass


class BinanceOrderManager(OrderManagerBase):
    Order = BinanceOrder

    def __init__(self, api, ws=None, external=True, retention=60):
        wsud = BinanceWebsocketUserData(api)  # ws is unused
        wsud.add_callback(self.__on_events)
        super().__init__(api, wsud, external, retention)

    def _after_auth(self):
        pass  # do nothing

    def _get_order_id(self, e):
        return str(e.o['i'])

    def _update_order(self, o, e):
        ts = e.E / 1000
        now = time.time()
        eo = e.o
        t = eo['x']
        if t == 'NEW':
            o.open_ts = ts
            o.state, o.state_ts = OPEN, now
        elif t == 'PARTIAL_FILL':
            pass  # do nothing
        elif t == 'FILL':
            pass  # do nothing
        elif t in ['CANCELED', 'REJECTED', 'EXPIRED']:
            o.close_ts = ts
            o.state, o.state_ts = CANCELED, now
        elif t == 'PENDING_CANCEL':
            pass  # do nothing
        elif t == 'CALCULATED':
            pass  # TODO
        elif t == 'TRADE':
            pass  # ?
        elif t == 'RESTATED':
            o.price = float(eo['p'])
            o.amount = float(eo['q'])
        else:
            self.log.error(f'Unknown event type: {t}')

        filled = float(eo['z'])
        if filled != o.filled:
            o.trade_ts = ts
            o.filled = filled
        if eo['X'] == 'FILLED':
            o.close_ts = ts
            o.state, o.state_ts = CLOSED, now

    def _create_external_order(self, e):
        o = e.o
        symbol = ccxt_binance.markets_by_id[o['s']]['symbol']
        return self.Order(
            symbol, o['o'].lower(), o['S'].lower(),
            float(o['q']), float(o['p']))

    def __on_events(self, msg):
        import pprint
        pprint.pprint(msg)

        e = BinanceOrderEvent()
        e.__dict__ = msg
        type_ = msg['e']
        if type_ == 'ACCOUNT_UPDATE':
            pass
        elif type_ == 'ORDER_TRADE_UPDATE':
            self._handle_order_event(e)
        else:
            self.log.warn(f'Unknown event type "{e}"')


class BinancePositionGroup(PositionGroupBase):
    def __init__(self):
        super().__init__()
        self.commission = 0  # total commissions in USD

    def update(self, price, size, commission):
        super().update(price, size)
        self.position = round(self.position, 8)
        self.commission += commission
        self.pnl -= commission


class BinanceOrderGroup(OrderGroupBase):
    PositionGroup = BinancePositionGroup

    def _handle_event(self, e):
        o = e.o
        p, s, c = float(o['L']), float(o['l']), float(o.get('n') or 0)
        if not s:
            return

        s = s if o['S'].lower() == BUY else -s
        self.position_group.update(p, s, c)


class BinanceOrderGroupManager(OrderGroupManagerBase):
    OrderGroup = BinanceOrderGroup


class BinanceOrderEvent:
    pass
    # Binance USER DATA STREAM (future)
    # https://binanceapitest.github.io/Binance-Futures-API-doc/userdatastream/
