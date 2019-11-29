class OrderInfo(dict):
    def __init__(self, symbol, type_, side, amount, price=0):
        super().__init__()
        self.__dict__ = self

        # Order Placement Info (Compliant with ccxt)
        self.symbol = symbol
        self.type = type_
        self.side = side
        self.amount = amount
        self.price = price

        # Order Management Info
        self.id = None          # exchange specific id
        self.filled = 0         # number of contracts
        self.state = None       # state managed by OrderManager
        self.state_ts = None    # timestamp of last state change
        self.trade_ts = None    # timestamp of last contract
        self.open_ts = None     # open timestamp
        self.close_ts = None    # close timestamp
        self.external = False   # True if order is created outside OrderManager
        self.event_cb = None    # callback: cb(event)
        self.group_name = None  # OrderGroup name


class PositionGroupBase(dict):
    def __init__(self):
        super().__init__()
        self.__dict__ = self
        self.position = 0
        self.gain = 0
        self.pnl = 0
        self.unrealized_pnl = 0

    def update(self, price, size):
        pos, gain = size, price * -size
        new_pos = self.position + pos

        if self.position * size >= 0:
            new_gain = self.gain + gain
        else:
            p, g = (pos, gain) if new_pos * \
                pos > 0 else (self.position, self.gain)
            new_gain = g * new_pos / p

        self.pnl += self.gain + gain - new_gain
        self.position = new_pos
        self.gain = new_gain
        self.update_unrealized_pnl(price)

    def update_unrealized_pnl(self, price):
        self.unrealized_pnl = self.gain + price * self.position
