import time
import logging
import collections
import threading
import traceback

from ..etc.util import decimal_add, run_forever_nonblocking, Timer


# Order Side
BUY = 'buy'
SELL = 'sell'

# Order Type
LIMIT = 'limit'
MARKET = 'market'

# Order State
OPEN = 'open'
CLOSED = 'closed'
CANCELED = 'canceled'
WAIT_OPEN = 'wait_open'
WAIT_CANCEL = 'wait_cancel'

# Order Event
EVENT_EXECUTION = 'execution'
EVENT_OPEN = 'open'
EVENT_CANCEL = 'cancel'
EVENT_OPEN_FAILED = 'open_failed'
EVENT_CANCEL_FAILED = 'cancel_failed'
EVENT_CLOSE = 'close'
EVENT_ERROR = 'error'


class Order(dict):
    def __init__(self, symbol, type_, side, amount, price=None, params={}):
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


class OrderEvent(dict):
    def __init__(self):
        super().__init__()
        self.__dict__ = self
        self.id = None
        self.ts = None
        self.type = None
        self.price = None    # EVENT_EXECUTION
        self.size = None     # EVENT_EXECUTION buy: size > 0, sell: size < 0
        self.message = None
        self.info = None


class OrderManagerBase:
    def __init__(self, api, ws, retention=60):
        self.log = logging.getLogger(self.__class__.__name__)
        self.api = api  # Api object
        self.ws = ws  # Websocket class (with auth)
        self.ws.add_after_auth_callback(self._after_auth)
        self.retention = retention  # retantion time of closed(canceled) order
        self.last_update_ts = 0
        self.orders = {}  # {id: Order}

        self.count_lock = 0
        self.__closed_orders = collections.deque()
        self.__event_queue = collections.deque()
        self.__check_timer = Timer(60)  # timer for check_open_orders
        self.__last_check_tss = {}  # {symbol: last_check_open_orders_ts}

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order(
            self, symbol, type_, side, amount, price=None, params={}):
        try:
            self.count_lock += 1
            res = self.api.create_order(
                symbol, type_, side, amount, price, params)
            o = Order(symbol, type_, side, amount, price, params)
            o.id = res['id']
            o.state, o.state_ts = WAIT_OPEN, time.time()
            self.orders[o.id] = o
        finally:
            self.count_lock -= 1

        return o

    def cancel_order(self, o):
        try:
            self.api.cancel_order(o.id, o.symbol)
        finally:
            if o.state in [OPEN, WAIT_OPEN]:
                o.state = WAIT_CANCEL
                o.state_ts = time.time()

    def cancel_external_orders(self, symbol):
        for o in self.orders.values():
            if o.external and o.symbol == symbol and o.state == OPEN:
                self.log.warning(
                    f'cancel external order: {o.id}')
                self.cancel_order(o)

    def _handle_order_event(self, e):
        o = self.orders.get(e.id)
        if o:
            self.__update_order(o, e)
        else:
            # if event comes before create_order returns
            # or order is not created by this class
            self.__event_queue.append(e)

    def _after_auth(self):
        assert False
        return self

    def _generate_order_object(self, e):
        assert False
        return self

    def __update_order(self, o, e):
        now = time.time()
        t = e.type
        st = o.state
        if t == EVENT_EXECUTION:
            o.filled, o.trade_ts = decimal_add(o.filled, abs(e.size)), now
            if o.state == WAIT_OPEN:
                o.state, o.open_ts = OPEN, e.ts
                self.log.warning('got an execution for a not "open" order')
        elif t == EVENT_OPEN:
            o.state, o.open_ts = OPEN, e.ts
        elif t == EVENT_CANCEL:
            o.state, o.close_ts = CANCELED, e.ts
        elif t == EVENT_OPEN_FAILED:
            o.state = CANCELED
            self.log.warning('failed to create order')
        elif t == EVENT_CANCEL_FAILED:
            if o.state == WAIT_CANCEL:
                o.state = OPEN
            self.log.warning('failed to cancel order')
        elif t == EVENT_CLOSE:
            o.state, o.close_ts = CLOSED, e.ts
        elif t == EVENT_ERROR:
            self.log.error(e.message)
        else:
            self.log.error(f'unhandled order event: {e}')

        if o.filled >= o.amount:
            o.state, o.close_ts = CLOSED, e.ts
            if o.filled > o.amount:
                self.log.error('Filled size is larger than order amount')

        if e.message and t != EVENT_ERROR:
            self.log.warn(e.message)

        if o.state != st:
            o.state_ts = now
        if o.state in [CLOSED, CANCELED]:
            self.__closed_orders.append(o)

        self.last_update_ts = now
        if o.event_cb:
            o.event_cb(e)

    def __process_queued_order_event(self):
        if self.count_lock:
            return

        while self.__event_queue:
            e = self.__event_queue.popleft()
            o = self.orders.get(e.id)
            if not o:  # if order is not created by this class
                o = self._generate_order_object(e)
                if not o:  # failed to external create order
                    continue
                o.id = e.id
                o.external = True
                o.state, o.state_ts = WAIT_OPEN, time.time()
                self.orders[o.id] = o
                self.log.debug(f'found external order: {o.id}')

            self.__update_order(o, e)

    def __remove_closed_orders(self):
        while self.__closed_orders:
            o = self.__closed_orders[0]
            if time.time() - o.state_ts > self.retention:
                self.__closed_orders.popleft()
                if o.state in [CLOSED, CANCELED]:
                    self.orders.pop(o.id, None)
            else:
                break

    def __check_orders(self):
        if not self.__check_timer.is_interval():
            return

        now = time.time()

        # remove orders closed(or canceled) more then twice retention time ago
        rm_orders = []
        for o in self.orders.values():
            if o.state in [CLOSED, CANCELED] \
                    and now - o.state_ts > self.retention * 2:
                rm_orders.append(o)

        for o in rm_orders:
            del self.orders[o.id]

        # check if there are 'open' orders which are already closed
        # find orders whose state_ts is more than retention time ago
        orders = []
        for o in self.orders.values():
            if o.state not in [CLOSED, CANCELED] \
                    and now - o.state_ts > self.retention:
                orders.append(o)

        if not orders:
            return

        # find the symbol with the oldest check timestamp
        oldest_ts, symbol = now, None
        for o in orders:
            ts = self.__last_check_tss.get(o.symbol, 0)
            if ts < oldest_ts:
                oldest_ts, symbol = ts, o.symbol
        self.__last_check_tss[symbol] = now

        # set actually closed(or canceled) orders state as 'canceled'
        self.log.debug(f'check if open orders for {symbol} are still alive')
        open_orders = self.api.fetch_open_orders(symbol)
        ids = [o['id'] for o in open_orders]
        for o in orders:
            if o.symbol != symbol:
                continue

            if o.id not in ids:
                self.log.warning(
                    f'order "{o.id}" is already closed or canceled.')
                o.state, o.state_ts = CANCELED, now
                self.__closed_orders.append(o)

    def __worker(self):
        self.__process_queued_order_event()
        self.__remove_closed_orders()
        self.__check_orders()


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

    def update(self, price, size, *args):
        avg0, pos0 = self.average_price, self.position
        avg1, pos1 = price, size
        pos = decimal_add(pos0, pos1)

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
        self.event_cb = []

    def create_order(self, type_, side, amount, price=None, params={}):
        om = self.manager.order_manager
        o = None
        try:
            om.count_lock += 1
            res = om.api.create_order(
                self.symbol, type_, side, amount, price, params)
            o = Order(self.symbol, type_, side, amount, price, params)
            o.event_cb = self.__handle_event
            o.group_name = self.name
            o.id = res['id']
            o.state, o.state_ts = WAIT_OPEN, time.time()
            om.orders[o.id] = o
            self.orders[o.id] = o
        finally:
            om.count_lock -= 1
            if self.order_log:
                self.order_log.info(
                    f'create order: {self.symbol} {type_} {side} '
                    f'{amount} {price} {params} => {o and o.id}')

        return o

    def cancel_order(self, o):
        om = self.manager.order_manager
        try:
            om.api.cancel_order(o.id, o.symbol)
        finally:
            if o.state in [OPEN, WAIT_OPEN]:
                o.state = WAIT_CANCEL
                o.state_ts = time.time()
            if self.order_log:
                self.order_log.info(f'cancel order: {o.id}')

    def set_order_log(self, log):
        self.order_log = log

    def set_closed_order_retention(self, sec):
        self.retention = sec

    def add_event_callback(self, cb):
        self.event_cb.append(cb)

    def remove_event_callback(self, cb):
        self.event_cb.remove(cb)

    def remove_closed_orders(self, retention=0):
        now = time.time()
        rm_id = []
        for id_, o in self.orders.items():
            if o.state in [CLOSED, CANCELED]:
                if now - o.state_ts > retention:
                    rm_id.append(id_)

        for id_ in rm_id:
            del self.orders[id_]

    def __handle_event(self, e):
        if e.type == EVENT_EXECUTION:
            self.position_group.update(e.price, e.size, e.info)

        for cb in self.event_cb:
            try:
                cb(e)
            except Exception:
                self.log.error(traceback.format_exc())


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
                total = decimal_add(total, og.position_group.position)
        return total

    def get_last_update_timestamp(self, symbol):
        ts = 0
        for og in self.order_groups.values():
            if og.symbol == symbol:
                ts = max(ts, og.position_group.last_update_ts)
        return ts

    def set_position_sync_config(
            self, symbol, min_lot, max_lot, position_func=None,
            action_filter=None, check_interval=60, update_margin=1):
        self.position_sync_configs[symbol] = PositionSyncConfig(
            symbol, min_lot, max_lot, position_func,
            action_filter, check_interval, update_margin)

    def _worker_destroy_order_group(self, og):
        while og.orders:  # cancel all order
            for _, o in og.orders.items():
                if o not in [CLOSED, CANCELED]:
                    try:
                        og.cancel_order(o)
                    except Exception as e:
                        og.log.error(e)
            time.sleep(3)
            og.remove_closed_orders()
        og.log.info('deleted')

    def __remove_closed_orders(self):
        for og in self.order_groups.values():
            og.remove_closed_orders(og.retention)

    def __update_unrealized_pnl(self):
        for og in self.order_groups.values():
            t = self.trades.get(og.symbol)
            if t and t.ltp:
                og.position_group.update_unrealized_pnl(t.ltp)

    def __check_position_integrity(self):
        # check if positions between server and client correspond
        now = time.time()
        for conf in self.position_sync_configs.values():
            if now - conf.last_check_ts < conf.check_interval:
                continue

            self.order_manager.cancel_external_orders(conf.symbol)

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
            if conf.position_func:
                server = conf.position_func()
            else:
                server = self.order_manager.api.fetch_position(conf.symbol)
            client = self.get_total_position(conf.symbol)

            ts1 = self.get_last_update_timestamp(conf.symbol)
            if ts0 != ts1:
                # client position is updated during getting server position
                continue

            if server == client:
                conf.position_diff = 0
                continue

            diff = decimal_add(client, -server)
            if diff == conf.position_diff:
                # start thread to fix mismatch
                # if previous diff and current diff matches
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

    def __fix_postion_mismatch(self, conf):
        self.log.warning(
            f'started to fix position mismatch for {conf.symbol}. '
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
                    size = decimal_add(diff, -pg.position)
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
                time.sleep(10)

        conf.is_position_sync_active = False
        conf.position_diff = 0

        self.destroy_order_group(og)

        self.log.warning(
            f'finished to fix position mismatch for {conf.symbol}.')

    def __worker(self):
        self.__remove_closed_orders()
        self.__update_unrealized_pnl()
        self.__check_position_integrity()


class PositionSyncConfig:
    def __init__(
            self, symbol, min_lot, max_lot, position_func,
            action_filter, check_interval, update_margin):
        self.symbol = symbol
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.position_func = position_func
        self.action_filter = action_filter
        self.check_interval = check_interval
        self.update_margin = update_margin
        self.last_check_ts = 0
        self.position_diff = 0
        self.is_position_sync_active = False
