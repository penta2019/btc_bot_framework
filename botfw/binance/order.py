from ..base import order as od
from .websocket_user_data import (
    BinanceWebsocketUserData, BinanceFutureWebsocketUserData)
from .api import ccxt_binance


class BinanceOrderManager(od.OrderManagerBase):
    WebsocketUserData = BinanceWebsocketUserData

    def __init__(self, api, ws=None, retention=60):
        wsud = self.WebsocketUserData(api)  # ws is unused
        wsud.add_callback(self.__on_events)
        super().__init__(api, wsud, retention)

    def _after_auth(self):
        pass  # do nothing

    def _generate_order_object(self, e):
        o = e.info['o']
        symbol = ccxt_binance().markets_by_id[o['s']]['symbol']
        return od.Order(
            symbol, o['o'].lower(), o['S'].lower(),
            float(o['q']), float(o['p']))

    def __on_events(self, msg):
        e = msg
        type_ = msg['e']
        if type_ == 'ACCOUNT_UPDATE':
            pass
        elif type_ == 'ORDER_TRADE_UPDATE':
            o = e['o']
            oe = od.OrderEvent()
            oe.info = e
            oe.id = str(o['i'])
            oe.ts = e['E'] / 1000

            t = o['x']
            size = float(o['l'])
            if size:
                oe.type = od.EVENT_EXECUTION
                oe.price = float(o['L'])
                oe.size = size if o['S'] == 'BUY' else -size
            elif t == 'NEW':
                oe.type = od.EVENT_OPEN
            elif t == 'PARTIAL_FILL':
                pass  # do nothing
            elif t == 'FILL':
                oe.type = od.EVENT_CLOSE
            elif t in ['CANCELED', 'EXPIRED']:
                oe.type = od .EVENT_CANCEL
            elif t == 'PENDING_CANCEL':
                pass  # do nothing
            elif t == 'REJECTED':
                oe.type = od.EVENT_OPEN_FAILED
            elif t == 'CALCULATED':
                pass  # TODO
            elif t == 'TRADE':
                pass  # Execution?
            elif t == 'RESTATED':
                pass  # TODO
                # price = float(o['p'])
                # amount = float(o['q'])
            else:
                self.log.error(f'Unknown order event type: {t}')

            self._handle_order_event(oe)
        else:
            self.log.warning(f'Unknown event type: {type_}')


class BinancePositionGroup(od.PositionGroupBase):
    def __init__(self):
        super().__init__()
        self.commission = 0  # total commissions in USD

    def update(self, price, size, info):
        super().update(price, size)
        commission = float(info['o'].get('n') or 0)
        self.commission += commission
        self.pnl -= commission


class BinanceOrderGroup(od.OrderGroupBase):
    PositionGroup = BinancePositionGroup


class BinanceOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BinanceOrderGroup


# Future
class BinanceFutureOrderManager(BinanceOrderManager):
    WebsocketUserData = BinanceFutureWebsocketUserData


class BinanceFuturePositionGroup(BinancePositionGroup):
    pass


class BinanceFutureOrderGroup(BinanceOrderGroup):
    PositionGroup = BinanceFuturePositionGroup


class BinanceFutureOrderGroupManager(BinanceOrderGroupManager):
    OrderGroup = BinanceFutureOrderGroup
