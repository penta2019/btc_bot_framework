import time
import logging
import collections
import threading
import traceback
import concurrent.futures

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
        self.trade_ts = None    # timestamp of last execution
        self.open_ts = None     # open timestamp
        self.close_ts = None    # close timestamp
        self.editing = False    # True if order is being edited
        self.external = False   # True if order is created outside OrderManager

        # Order Group Mangement Info
        self.group_name = None  # OrderGroup name
        self.event_cb = None    # callback: cb(event)


class OrderEvent(dict):
    def __init__(
            self, id_=None, ts=None, type_=None,  # basic info
            price=None, size=None, fee=None,      # for EVENT_EXECUTON
            message=None, info=None):             # additional info
        super().__init__()
        self.__dict__ = self
        self.id = id_
        self.ts = ts
        self.type = type_

        self.price = price  # EVENT_EXECUTION
        self.size = size    # EVENT_EXECUTION buy: size > 0, sell: size < 0
        self.fee = fee      # EVENT_EXECUTION

        self.message = message
        self.info = info


class OrderManagerBase:
    def __init__(self, api, ws, retention=60):
        self.log = logging.getLogger(self.__class__.__name__)
        self.api = api  # Api object
        self.ws = ws  # Websocket class (with auth)
        self.retention = retention  # retantion time of closed(canceled) order
        self.timeout = 30

        self.last_update_ts = 0
        self.orders = {}  # {id: Order}
        self.pending_orders = []

        self.__zombie_orders = collections.deque()  # [(ts, Order)]
        self.__closed_orders = collections.deque()  # [Order]
        self.__event_queue = collections.deque()  # [OrderEvent]
        self.__check_timer = Timer(60)  # timer for check_open_orders
        self.__last_check_tss = {}  # {symbol: last_check_open_orders_ts}
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order(
            self, symbol, type_, side, amount, price=None, params={},
            event_cb=None, log=None, sync=False):
        if sync:
            o = None
            try:
                self.pending_orders.append(None)
                res = self.api.create_order(
                    symbol, type_, side, amount, price, params)
                o = Order(symbol, type_, side, amount, price, params)
                o.id = res['id']
                o.state, o.state_ts = WAIT_OPEN, time.time()
                o.event_cb = event_cb
                self.orders[o.id] = o
            finally:
                self.pending_orders.remove(None)
                if log:
                    log.info(
                        f'create order(sync): {symbol} {type_} {side} '
                        f'{amount} {price} {params} => {o and o.id}')
        else:
            o = Order(symbol, type_, side, amount, price, params)
            o.state, o.state_ts = WAIT_OPEN, time.time()
            o.event_cb = event_cb
            self.pending_orders.append(o)

            f = self.__executor.submit(
                self.api.create_order,
                symbol, type_, side, amount, price, params)
            f.add_done_callback(
                lambda f: self.__handle_create_order(o, log, f))
        return o

    def cancel_order(self, o, log=None, sync=False):
        elog = log or self.log

        if not o.id:
            if o.state == WAIT_OPEN \
                    and time.time() - o.state_ts < self.timeout:
                elog.error('cancel failed: order has not accepted yet')
            else:
                o.state = CANCELED
                elog.error('cancel failed: invalid order')
            return

        if o.state in [OPEN, WAIT_OPEN]:
            o.state, o.state_ts = WAIT_CANCEL, time.time()

        if sync:
            try:
                self.api.cancel_order(o.id, o.symbol)
            except Exception as e:
                o.state, o.state_ts = CANCELED, time.time()
                elog.error(f'{type(e).__name__}: {e}')
            finally:
                if log:
                    log.info(f'cancel order: {o.id}')
        else:
            f = self.__executor.submit(self.api.cancel_order, o.id, o.symbol)
            f.add_done_callback(
                lambda f: self.__handle_cancel_order(o, log, f))

        if o.id not in self.orders and o not in self.pending_orders:
            o.state = CANCELED
            elog.error(f'cancel failed: Order {o.id} is not in order list')

    def edit_order(self, o, amount=None, price=None, log=None, sync=False):
        o.editing = True
        if sync:
            try:
                res = self.api.edit_order(
                    o.id, o.symbol, o.type, o.side,
                    amount or o.amount, price or o.price)
                o.price = res['price']
                o.amount = res['amount']
            finally:
                o.editing = False
                if o.filled >= o.amount:
                    o.state, o.close_ts = CLOSED, time.time()
                if log:
                    log.info(
                        f'edit order: {o.symbol} {o.type} {o.side} '
                        f'{o.amount} {o.price} {o.params} => {o.id}')
        else:
            f = self.__executor.submit(
                self.api.edit_order,
                o.id, o.symbol, o.type, o.side,
                amount or o.amount, price or o.price)
            f.add_done_callback(
                lambda f: self.__handle_edit_order(o, log, f))
        return o

    def cancel_external_orders(self, symbol):
        for o in self.orders.values():
            if o.external and o.symbol == symbol and o.state == OPEN:
                self.log.warning(f'cancel external order: {o.id}')
                self.cancel_order(o)

    def _handle_order_event(self, e):
        o = self.orders.get(e.id)
        if o:
            self.__update_order(o, e)
        else:
            # if event comes before create_order returns
            # or order is not created by this class
            self.__event_queue.append(e)

    def _generate_order_object(self, e) -> Order:
        assert False
        return self

    def __update_order(self, o, e):
        now = time.time()
        t = e.type
        st = o.state
        if t == EVENT_EXECUTION:
            o.filled, o.trade_ts = decimal_add(o.filled, abs(e.size)), now
            if o.state in [CLOSED, CANCELED]:
                self.log.warning(
                    f'got an execution for a closed order: {e.id}')
            if o.state == WAIT_OPEN:
                o.state, o.open_ts = OPEN, e.ts
            elif not o.open_ts:
                o.open_ts = e.ts
        elif t == EVENT_OPEN:
            if o.state == WAIT_OPEN:
                o.state, o.open_ts = OPEN, e.ts
            else:
                o.open_ts = e.ts
        elif t == EVENT_CANCEL:
            o.state, o.close_ts = CANCELED, e.ts
        elif t == EVENT_OPEN_FAILED:
            o.state = CANCELED
            self.log.warning(f'failed to create order: {e.id}')
        elif t == EVENT_CANCEL_FAILED:
            if o.state == WAIT_CANCEL:
                o.state = OPEN
            self.log.warning(f'failed to cancel order: {e.id}')
        elif t == EVENT_CLOSE:
            o.state, o.close_ts = CLOSED, e.ts
        elif t == EVENT_ERROR:
            self.log.error(e.message)
        else:
            self.log.error(f'unhandled order event: {e}')

        if o.filled >= o.amount and not o.editing:
            o.state, o.close_ts = CLOSED, e.ts
            if o.filled > o.amount:
                self.log.error(
                    f'Filled size is larger than order amount: {e.id}')

        if e.message and t != EVENT_ERROR:
            self.log.warning(f'{e.message}: {e.id}')

        if o.state != st:
            o.state_ts = now
        if o.state in [CLOSED, CANCELED]:
            self.__closed_orders.append(o)

        self.last_update_ts = now
        if o.event_cb:
            o.event_cb(e)

    def __process_queued_order_event(self):
        if self.pending_orders:
            return

        while self.__event_queue:
            e = self.__event_queue.popleft()
            o = self.orders.get(e.id)
            if not o:  # if order is not created by this class
                o = self._generate_order_object(e)
                if not o:
                    continue
                o.id = e.id
                o.external = True
                o.state, o.state_ts = WAIT_OPEN, time.time()
                self.orders[o.id] = o
                self.log.debug(f'found external order: {o.id}')

            self.__update_order(o, e)

    def __remove_closed_orders(self):
        now = time.time()

        while self.__zombie_orders:
            ts, o = self.__zombie_orders[0]
            if now - ts > self.timeout:
                self.__zombie_orders.popleft()
                if o.state not in [CLOSED, CANCELED]:
                    self.log.warning(
                        f'order "{o.id}" is already closed or canceled.')
                    o.state, o.state_ts = CANCELED, now
                    self.__closed_orders.append(o)
            else:
                break

        while self.__closed_orders:
            o = self.__closed_orders[0]
            if now - o.state_ts > self.retention:
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

        # find open orders
        open_orders = [o for o in self.orders.values()
                       if o.state not in [CLOSED, CANCELED]]

        if not open_orders:
            return

        # find a symbol with the oldest check timestamp
        oldest_ts, symbol = now, None
        for o in open_orders:
            ts = self.__last_check_tss.get(o.symbol, 0)
            if ts < oldest_ts:
                oldest_ts, symbol = ts, o.symbol
        self.__last_check_tss[symbol] = now

        # find zombie orders('open' state, but actually closed)
        ids = [o['id'] for o in self.api.fetch_open_orders(symbol)]
        for o in open_orders:
            if o.symbol == symbol and o.id not in ids:
                self.log.debug(f'found a zombie order: {o.id}')
                self.__zombie_orders.append((now, o))

    def __handle_create_order(self, o, log, f):
        try:
            res = f.result()
            o.id = res['id']
            self.orders[o.id] = o
        except Exception as e:
            o.state, o.state_ts = CANCELED, time.time()
            (log or self.log).error(f'{type(e).__name__}: {e}')
        finally:
            self.pending_orders.remove(o)
            if log:
                log.info(
                    f'create order: {o.symbol} {o.type} {o.side} '
                    f'{o.amount} {o.price} {o.params} => {o.id}')

    def __handle_cancel_order(self, o, log, f):
        try:
            f.result()
        except Exception as e:
            if o.state == WAIT_CANCEL:
                o.state, o.state_ts = OPEN, time.time()
            (log or self.log).error(f'{type(e).__name__}: {e}')
        finally:
            if log:
                log.info(f'cancel order: {o.id}')

    def __handle_edit_order(self, o, log, f):
        try:
            res = f.result()
            o.price = res['price']
            o.amount = res['amount']
        except Exception as e:
            (log or self.log).error(f'{type(e).__name__}: {e}')
        finally:
            o.editing = False
            if o.filled >= o.amount:
                o.state, o.close_ts = CLOSED, time.time()
            if log:
                log.info(
                    f'edit order: {o.symbol} {o.type} {o.side} '
                    f'{o.amount} {o.price} {o.params} => {o.id}')

    def __worker(self):
        self.__process_queued_order_event()
        self.__remove_closed_orders()
        self.__check_orders()


class PositionGroupBase(dict):
    SIZE_IN_QUOTE = False

    def __init__(self):
        super().__init__()
        self.__dict__ = self
        self.position = 0
        self.pnl = 0
        self.unrealized_pnl = 0
        self.fee = 0
        self.average_price = 1
        self.last_update_ts = 0

    def update(self, price, size, fee=0, *args):
        avg0, pos0 = self.average_price, self.position
        avg1, pos1 = price, size
        pos = decimal_add(pos0, pos1)

        if pos == 0:
            avg = 1
        elif pos0 * pos1 >= 0:
            if self.SIZE_IN_QUOTE:
                avg = (pos0 + pos1) / (pos0 / avg0 + pos1 / avg1)
            else:
                avg = (avg0 * pos0 + avg1 * pos1) / pos
        elif pos * pos0 > 0:
            avg = avg0
        else:  # pos * pos1 > 0
            avg = avg1

        if self.SIZE_IN_QUOTE:
            pnl = ((pos0 / avg0) + (pos1 / avg1) - (pos / avg)) * price
        else:
            pnl = avg * pos - avg0 * pos0 - avg1 * pos1

        self.position = pos
        self.average_price = avg
        self.pnl += pnl - fee
        self.fee += fee
        self.update_unrealized_pnl(price)
        self.last_update_ts = time.time()

    def update_unrealized_pnl(self, price):
        if self.SIZE_IN_QUOTE:
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
        self.order_log = None
        self.position_group = self.PositionGroup()
        self.event_cb = []

    def create_order(
            self, type_: str, side: str, amount: float, price: float = None,
            params: dict = {}, sync: bool = False) -> Order:
        o = self.manager.order_manager.create_order(
            self.symbol, type_, side, amount, price, params,
            self.__handle_event, self.order_log, sync)
        o.group_name = self.name
        return o

    def cancel_order(self, o: Order, sync: bool = False) -> None:
        self.manager.order_manager.cancel_order(o, self.order_log, sync)

    def edit_order(
            self, o: Order, amount: float = None, price: float = None,
            sync: bool = False) -> Order:
        o = self.manager.order_manager.edit_order(
            o, amount, price, self.order_log, sync)
        return o

    def get_orders(self):
        orders = {}
        for o in self.manager.order_manager.orders.values():
            if o.get('group_name') == self.name:
                orders[o.id] = o
        return orders

    def set_order_log(self, log):
        self.order_log = log

    def add_event_callback(self, cb):
        self.event_cb.append(cb)

    def remove_event_callback(self, cb):
        self.event_cb.remove(cb)

    def __handle_event(self, e):
        if e.type == EVENT_EXECUTION:
            self.position_group.update(e.price, e.size, e.fee, e.info)

        for cb in self.event_cb:
            try:
                cb(e)
            except Exception:
                self.log.error(traceback.format_exc())


class OrderGroupManagerBase:
    OrderGroup = OrderGroupBase

    def __init__(self, order_manager, trades={}):
        self.log = logging.getLogger(self.__class__.__name__)
        self.order_manager = order_manager
        self.order_groups = {}
        self.position_sync_configs = {}
        self.trades = trades  # {symbol:Trade}, used to update unrealized pnl

        run_forever_nonblocking(self.__worker, self.log, 1)

    def create_order_group(self, symbol, name):
        if name in self.order_groups:
            self.log.error('Failed to create order group. '
                           f'Order group "{name}" already exists.')
            return None

        og = self.OrderGroup(self, symbol, name)
        self.order_groups[name] = og
        og.log.info('created')
        return og

    def destroy_order_group(self, og, cancel_orders=True):
        name = og.name
        if name not in self.order_groups:
            self.log.error('Failed to destroy order group. '
                           f'Unknown order group "{name}". ')
        og = self.order_groups.pop(name)
        if cancel_orders:
            for _, o in self.order_manager.orders.items():
                if o.group_name == name and o.state in [WAIT_OPEN, OPEN]:
                    og.cancel_order(o)

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

        o = None
        while pg.position != diff:
            try:
                if not o or o.state in [CLOSED, CANCELED]:
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
                        o = og.create_order(MARKET, BUY, size)
                    else:
                        o = og.create_order(MARKET, SELL, -size)
                time.sleep(3)
            except Exception:
                og.log.error(traceback.format_exc())
                time.sleep(10)

        conf.is_position_sync_active = False
        conf.position_diff = 0

        self.destroy_order_group(og)

        self.log.warning(
            f'finished to fix position mismatch for {conf.symbol}.')

    def __worker(self):
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
