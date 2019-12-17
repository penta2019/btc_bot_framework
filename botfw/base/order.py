import time
import logging
import collections
import threading
import traceback

from ..etc.util import decimal_sum, run_forever_nonblocking


# Order Side
BUY = 'buy'
SELL = 'sell'

# Order Type
LIMIT = 'limit'
MARKET = 'market'

# Order state
OPEN = 'open'
CLOSED = 'closed'
CANCELED = 'canceled'
WAIT_OPEN = 'wait_open'
WAIT_CANCEL = 'wait_cancel'


class OrderBase(dict):
    def __init__(self, symbol, type_, side, amount, price=0, params={}):
        super().__init__()
        self.__dict__ = self

        # Order Placement Info (Compliant with ccxt)
        self.symbol = symbol
        self.type = type_
        self.side = side
        self.amount = amount
        self.price = price
        self.params = params

        # Order Management Info
        self.id = None          # exchange specific id
        self.filled = 0         # number of contracts
        self.state = None       # state managed by OrderManager
        self.state_ts = None    # timestamp of last state change
        self.trade_ts = None    # timestamp of last contract
        self.open_ts = None     # open timestamp
        self.close_ts = None    # close timestamp
        self.external = False   # True if order is created outside OrderManager

        # Order Group Mangement Info
        self.group_name = None  # OrderGroup name
        self.event_cb = None    # callback: cb(event)


class OrderManagerBase:
    Order = OrderBase

    def __init__(self, api, ws, external=True, retention=60):
        self.log = logging.getLogger(self.__class__.__name__)
        self.api = api  # Api object
        self.ws = ws  # Websocket class (with auth)
        self.ws.add_after_auth_callback(self._after_auth)
        self.external = external  # True to allow external orders
        self.retention = retention  # retantion time of closed(canceled) order
        self.last_update_ts = 0
        self.orders = {}  # {id: Order}

        self.__old_orders = collections.deque()
        self.__event_queue = collections.deque()
        self.__count_lock = 0

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order(self, symbol, type_, side, amount, price=0, params={}):
        o = self.Order(symbol, type_, side, amount, price, params)
        return self.create_order_internal(o)

    def create_order_internal(self, o):
        try:
            self.__count_lock += 1

            res = self.api.create_order(
                o.symbol, o.type, o.side, o.amount, o.price)
            o.id = res['id']
            o.state, o.state_ts = WAIT_OPEN, time.time()
            self.orders[o.id] = o
        finally:
            self.__count_lock -= 1

        return o

    def cancel_order(self, o):
        self.api.cancel_order(o.id, o.symbol)
        if o.state in [OPEN, WAIT_OPEN]:
            o.state = WAIT_CANCEL
            o.state_ts = time.time()

    def _handle_order_event(self, e):
        o = self.orders.get(self._get_order_id(e))
        if o:
            self.__update_order2(o, e)
        else:
            # if event comes before create_order returns
            # or order is not created by this class
            self.__event_queue.append(e)

    def _after_auth(self):
        assert False
        return 0

    def _get_order_id(self, e):
        assert False
        return 0

    def _update_order(self, o, e):
        assert False
        return 0

    def _create_external_order(self, e):
        assert False
        return 0

    def __update_order2(self, o, e):
        self._update_order(o, e)
        self.last_update_ts = time.time()
        if o.state in [CLOSED, CANCELED]:
            self.__old_orders.append(o)
        if o.event_cb:
            o.event_cb(e)

    def __process_queued_order_event(self):
        if self.__count_lock:
            return

        while self.__event_queue:
            e = self.__event_queue.popleft()
            i = self._get_order_id(e)
            o = self.orders.get(i)
            if not o:  # if order is not created by this class
                o = self._create_external_order(e)
                if not o:  # failed to external create order
                    continue
                o.id = self._get_order_id(e)
                o.external = True
                o.state, o.state_ts = WAIT_OPEN, time.time()
                self.orders[i] = o
            self._update_order(o, e)
            if o.event_cb:
                o.event_cb(e)

    def __cancel_external_orders(self):
        for o in self.orders.values():
            if o.external and o.state == OPEN:
                self.log.warning(
                    f'cancel external order: {o.id}')
                self.cancel_order(o)

    def __remove_old_order(self):
        while self.__old_orders:
            o = self.__old_orders[0]
            if time.time() - o.state_ts > self.retention:
                self.__old_orders.popleft()
                self.orders.pop(o.id, None)
            else:
                break

    def __worker(self):
        self.__process_queued_order_event()
        self.__remove_old_order()
        if not self.external:
            self.__cancel_external_orders()


class PositionGroupBase(dict):
    SIZE_IN_FIAT = False

    def __init__(self):
        super().__init__()
        self.__dict__ = self
        self.position = 0
        self.pnl = 0
        self.unrealized_pnl = 0
        self.average_price = 1
        self.last_update_ts = 0

    def update(self, price, size):
        avg0, pos0 = self.average_price, self.position
        avg1, pos1 = price, size
        pos = decimal_sum(pos0, pos1)

        if pos == 0:
            avg = 1
        elif pos0 * pos1 >= 0:
            if self.SIZE_IN_FIAT:
                avg = (pos0 + pos1) / (pos0 / avg0 + pos1 / avg1)
            else:
                avg = (avg0 * pos0 + avg1 * pos1) / pos
        elif pos * pos0 > 0:
            avg = avg0
        else:  # pos * pos1 > 0
            avg = avg1

        if self.SIZE_IN_FIAT:
            pnl = ((pos0 / avg0) + (pos1 / avg1) - (pos / avg)) * price
        else:
            pnl = avg * pos - avg0 * pos0 - avg1 * pos1

        self.position = pos
        self.average_price = avg
        self.pnl += pnl
        self.update_unrealized_pnl(price)
        self.last_update_ts = time.time()

    def update_unrealized_pnl(self, price):
        if self.SIZE_IN_FIAT:
            pnl = (1 / self.average_price - 1 / price) * self.position * price
        else:
            pnl = (price - self.average_price) * self.position
        self.unrealized_pnl = pnl


class OrderGroupBase:
    PositionGroup = PositionGroupBase

    def __init__(self, manager, symbol, name):
        self.log = logging.getLogger(
            f'{self.__class__.__name__}({name}@{symbol})')
        self.manager = manager
        self.symbol = symbol
        self.name = name
        self.retention = 60
        self.order_log = None
        self.position_group = self.PositionGroup()
        self.orders = {}

    def create_order(self, type_, side, amount, price=0, params={}):
        om = self.manager.order_manager
        o = om.Order(self.symbol, type_, side, amount, price, params)
        o.event_cb = self._handle_event
        o.group_name = self.name
        o = om.create_order_internal(o)
        self.orders[o.id] = o
        if self.order_log:
            self.order_log.info(
                f'create order: {self.symbol} {type_} {side} '
                f'{amount} {price} {params} => {o.id}')
        return o

    def cancel_order(self, o):
        self.manager.order_manager.cancel_order(o)
        if self.order_log:
            self.order_log.info(f'cancel order: {o.id}')

    def set_order_log(self, log):
        self.order_log = log

    def set_closed_order_retention(self, sec):
        self.retention = sec

    def remove_closed_orders(self, retention=0):
        now = time.time()
        rm_id = []
        for id_, o in self.orders.items():
            if o.state in [CLOSED, CANCELED]:
                if now - o.state_ts > retention:
                    rm_id.append(id_)

        for id_ in rm_id:
            del self.orders[id_]

    def _handle_event(self, e):
        assert False


class OrderGroupManagerBase:
    OrderGroup = OrderGroupBase

    def __init__(self, order_manager, retention=60, trades={}):
        self.log = logging.getLogger(self.__class__.__name__)
        self.order_manager = order_manager
        self.order_groups = {}
        self.position_sync_configs = {}
        self.trades = trades  # {symbol:Trade}, used to update unrealized pnl
        self.retention = retention

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order_group(self, symbol, name='NoName'):
        if name in self.order_groups:
            self.log.error('Failed to create order group. '
                           f'Order group "{name}" already exists.')
            return None

        og = self.OrderGroup(self, symbol, name)
        og.set_closed_order_retention(self.retention)
        self.order_groups[name] = og
        og.log.info('created')
        return og

    def destroy_order_group(self, og):
        name = og.name
        if name not in self.order_groups:
            self.log.error('Failed to destroy order group. '
                           f'Unknown order group "{name}". ')

        og = self.order_groups.pop(name)

        thread = threading.Thread(
            name=f'clean_{og.name}', target=self._worker_destroy_order_group,
            args=[og])
        thread.daemon = True
        thread.start()

    def get_total_position(self, symbol):
        total = 0
        for og in self.order_groups.values():
            if og.symbol == symbol:
                total = decimal_sum(total + og.position_group.position)
        return total

    def get_last_update_timestamp(self, symbol):
        ts = 0
        for og in self.order_groups.values():
            if og.symbol == symbol:
                ts = max(ts, og.position_group.last_update_ts)
        return ts

    def set_position_sync_config(
            self, symbol, position_func, min_lot, max_lot,
            action_filter=None, check_interval=60, update_margin=1):
        self.position_sync_configs[symbol] = PositionSyncConfig(
            symbol, position_func, min_lot, max_lot,
            action_filter, check_interval, update_margin)

    def _worker_destroy_order_group(self, og):
        while og.orders:  # cancel all order
            for id_, o in og.orders.items():
                if o not in [CLOSED, CANCELED]:
                    og.cancel_order(o)
                    og.log.info(f'cancel remaining order: {id_}')
            time.sleep(3)
            og.remove_closed_orders()
        og.log.info('deleted')

    def __fix_postion_mismatch(self, conf):
        self.log.warning(
            f'start to fix position mismatch for {conf.symbol}. '
            f'target_size={conf.position_diff}')

        og = self.create_order_group(conf.symbol, 'fix_position')
        og.set_order_log(og.log)

        conf.is_position_sync_active = True
        diff = conf.position_diff
        min_lot = conf.min_lot
        max_lot = conf.max_lot
        pg = og.position_group

        while pg.position != diff:
            try:
                if not og.orders:
                    size = decimal_sum(diff, -pg.position)
                    if size < -max_lot:
                        size = -max_lot
                    elif -min_lot < size < 0:
                        size = min_lot
                    elif 0 < size < min_lot:
                        size = -min_lot
                    elif max_lot < size:
                        size = max_lot

                    if size > 0:
                        og.create_order(MARKET, BUY, size)
                    else:
                        og.create_order(MARKET, SELL, -size)

                    time.sleep(3)
                    og.remove_closed_orders()
            except Exception:
                og.log.error(traceback.format_exc())

        conf.is_position_sync_active = False
        conf.position_diff = 0

        self.destroy_order_group(og)

        self.log.warning(f'finish to fix position mismatch for {conf.symbol}.')

    def __worker(self):
        # remove closed orders older than retention time
        for og in self.order_groups.values():
            og.remove_closed_orders(og.retention)

        # update unrealized pnl if possible
        for og in self.order_groups.values():
            t = self.trades.get(og.symbol)
            if t and t.ltp:
                og.position_group.update_unrealized_pnl(t.ltp)

        # check if positions between server and client correspond
        now = time.time()
        for conf in self.position_sync_configs.values():
            if now - conf.last_check_ts < conf.check_interval:
                continue

            if conf.is_position_sync_active:
                continue

            ts0 = self.get_last_update_timestamp(conf.symbol)
            if now - ts0 < conf.update_margin:
                # last position update margin is not enought
                continue

            conf.last_check_ts = now
            if conf.action_filter and not conf.action_filter():
                # user wants to skip position check this time
                continue

            self.log.debug(f'position integrity check for {conf.symbol}')

            # get server and client position
            server = conf.position_func()
            client = self.get_total_position(conf.symbol)

            ts1 = self.get_last_update_timestamp(conf.symbol)
            if ts0 != ts1:
                # client position is updated during getting server position
                continue

            if server == client:
                self.position_diff = 0
                continue

            diff = decimal_sum(client - server)
            if diff == conf.position_diff:
                # start thread to fix mismatch
                thread = threading.Thread(
                    name=f'fix_position@{conf.symbol}',
                    target=self.__fix_postion_mismatch,
                    args=[conf])
                thread.daemon = True
                thread.start()
            else:
                conf.position_diff = diff
                self.log.warning(
                    'detect position mismatch between '
                    f'server({server}) and client({client}).')


class PositionSyncConfig:
    def __init__(
            self, symbol, position_func, min_lot, max_lot,
            action_filter, check_interval, update_margin):
        self.symbol = symbol
        self.position_func = position_func
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.action_filter = action_filter
        self.check_interval = check_interval
        self.update_margin = update_margin
        self.last_check_ts = 0
        self.position_diff = 0
        self.is_position_sync_active = False
