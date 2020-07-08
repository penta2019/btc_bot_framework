import logging

from .order_simulator import OrderManagerSimulator

none = getattr(object, '__class__')  # silence linter


class ExchangeBase:  # Abstract Factory
    Api = none
    Websocket = none
    Trade = none
    Orderbook = none
    OrderManager = none
    OrderGroupManager = none

    def __init__(self, simulate=False):
        self.log = logging.getLogger(self.__class__.__name__)
        self.trades = {}
        self.orderbooks = {}
        self.api = None
        self.websocket = None
        self.order_manager = None
        self.order_group_manager = None
        self.simulate = simulate

    def init_account(self, ccxt_config={}):
        if not self.simulate:
            self.log.info('real trade mode')
            self.api = self.Api(ccxt_config)
            self.websocket = self.Websocket(
                ccxt_config['apiKey'], ccxt_config['secret'])
            self.order_manager = self.OrderManager(
                self.api, self.websocket)
            self.order_group_manager = self.OrderGroupManager(
                self.order_manager)
            self.order_manager.prepare_simulator = \
                lambda s: type('Dummy', (), {})
        else:
            self.log.info('simulation mode')
            ccxt_config['apiKey'] = None
            ccxt_config['secret'] = None
            self.api = self.Api(ccxt_config)
            self.websocket = self.Websocket(
                ccxt_config['apiKey'], ccxt_config['secret'])

            self.order_manager = OrderManagerSimulator(
                self.api, self.websocket, 60, self)
            self.order_group_manager = self.OrderGroupManager(
                self.order_manager)
            self.order_group_manager.set_position_sync_config =\
                lambda *args: self.log.warning(
                    'set_position_sync_config is ignored in simulation mode.')
        return {
            'api': self.api,
            'websocket': self.websocket,
            'order_manager': self.order_manager,
            'order_group_manager': self.order_group_manager,
        }

    def create_trade(self, symbol, ws=None):
        if symbol in self.trades:
            return self.trades[symbol]

        trade = self.Trade(symbol, ws)
        self.trades[symbol] = trade
        if self.order_group_manager:
            self.order_group_manager.trades[symbol] = trade
        return trade

    def create_orderbook(self, symbol, ws=None):
        if symbol in self.orderbooks:
            return self.orderbooks[symbol]

        orderbook = self.Orderbook(symbol, ws)
        self.orderbooks[symbol] = orderbook
        return orderbook

    def create_order_group(self, symbol, name=None):
        return self.order_group_manager.create_order_group(symbol, name)
