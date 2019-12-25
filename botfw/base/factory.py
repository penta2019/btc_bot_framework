def none(*args):
    assert False
    return args[0]


class FactoryBase:  # Abstract Factory
    Api = none
    Websocket = none
    Trade = none
    Orderbook = none
    OrderManager = none
    OrderGroupManager = none

    def __init__(self):
        self.api = None
        self.websocket = None
        self.order_manager = None
        self.order_group_manager = None

    def create_basics(self, ccxt_config):
        self.api = self.Api(ccxt_config)
        self.websocket = self.Websocket(
            ccxt_config['apiKey'], ccxt_config['secret'])
        self.order_manager = self.OrderManager(self.api, self.websocket)
        self.order_group_manager = self.OrderGroupManager(self.order_manager)
        return {
            'api': self.api,
            'websocket': self.websocket,
            'order_manager': self.order_manager,
            'order_group_manager': self.order_group_manager,
        }

    def create_trade(self, symbol, ws=None):
        trade = self.Trade(symbol, ws)
        if self.order_group_manager:
            self.order_group_manager.trades[symbol] = trade
        return trade

    def create_orderbook(self, symbol, ws=None):
        orderbook = self.Orderbook(symbol, ws)
        return orderbook

    def create_order_group(self, symbol, name=None):
        return self.order_group_manager.create_order_group(symbol, name)
