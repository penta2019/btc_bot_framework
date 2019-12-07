# import time

from ..base.order import (
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CANCELED, WAIT_OPEN, WAIT_CANCEL,
    OrderManagerBase, OrderBase,
    OrderGroupManagerBase, OrderGroupBase,
    PositionGroupBase
)
from .websocket_user_data import BinanceWebsocketUserData

# silence linter (imported but unused)
_DUMMY = [
    BUY, SELL,
    LIMIT, MARKET,
    OPEN, CLOSED, CLOSED, CANCELED,
    WAIT_OPEN, WAIT_CANCEL
]

# SPOT EVENTS
EVENT_OUTBOUND_ACCOUNT_INFO = 'outboundAccountInfo'
EVENT_OUTBOUND_ACCOUNT_POSITION = 'outboundAccountPosition'
EVENT_BALANCE_UPDATE = 'balanceUpdate'
EVENT_EXECUTION_REPORT = 'executionReport'
EVENT_LIST_STATUS = 'listStatus'

# FUTURE EVENTS
FUTURE_EVENT_ACCOUNT_UPDATE = 'ACCOUNT_UPDATE'
FUTURE_EVENT_ORDER_TRADE_UPDATE = 'ORDER_TRADE_UPDATE'


class BinanceOrder(OrderBase):
    pass


class BinanceOrderManager(OrderManagerBase):
    Order = BinanceOrder

    def __init__(self, api, ws=None, external=True, retention=60):
        wsud = BinanceWebsocketUserData(api)  # ws is unused
        wsud.add_callback(self.__on_events)
        super().__init__(api, wsud, external, retention)

    def _after_auth(self):
        self._init()

    def _handle_events(self):
        if self._count_lock:
            return

        while self._event_queue:
            e = self._event_queue.popleft()
            o = self.__get_order(e)
            if not o:
                pass
            self.__update_order(o, e)

    def __on_events(self, msg):
        import pprint
        pprint.pprint(msg)
        e = msg['e']
        if e == FUTURE_EVENT_ACCOUNT_UPDATE:
            pass
        elif e == FUTURE_EVENT_ORDER_TRADE_UPDATE:
            pass
        else:
            self.log.warn(f'Unknown event type "{e}"')

    def __update_order(self, o, e):
        pass

    def __get_order(self, e):
        pass


class BinancePositionGroup(PositionGroupBase):
    pass


class BinanceOrderGroup(OrderGroupBase):
    Order = BinanceOrder
    PositionGroup = BinancePositionGroup

    def _handle_event(self, e):
        pass


class BinanceOrderGroupManager(OrderGroupManagerBase):
    OrderGroup = BinanceOrderGroup
    PositionGroup = BinancePositionGroup

    def _worker_destroy_order_group(self, og):
        pass


class BinanceOrderEvent:
    pass

    # Binance USER DATA STREAM (future)
    # https://binanceapitest.github.io/Binance-Futures-API-doc/userdatastream/
    #
    # ACOUNT_UPDATE ----------------------------------------------------------
    # {
    #     "e": "ACCOUNT_UPDATE", // Event type
    #     "E": 1564745798939 // Event time
    #     "a": [
    #         {
    #       "B": [ // Balances
    #             {
    #                  "a": "USDT",            // Asset
    #                 "wb": "122624" // Wallet Balance
    #              },
    #              {
    #                  "a": "BTC",
    #                  "wb": "0"
    #                  }
    #             ],
    #       "P": [ // Positions
    #             {
    #                  "s": "BTCUSDT",         // Symbol
    #                 "pa": "1", // Position Amount
    #                  "ep": "9000", // Entry Price
    #                 "cr": "200" // (Pre - fee) accumulated realized
    #              }
    #             ]
    #         }
    #     ]
    # }
    #
    # ORDER_TRADE_UPDATE -----------------------------------------------------
    # {
    #     "e": "ORDER_TRADE_UPDATE", // Event type
    #     "E": 1564745798939 // Event time
    #     "o":
    #     {
    #         "s": "BTCUSDT", // Symbol
    #         "c": "211", // Client Order Id
    #         "S": "BUY", // Side
    #         "o": "LIMIT", // Order Type
    #         "f": "GTC", // Time In Force
    #         "q": "1.00000000", // Original quantity
    #         "p": "0.10264410", // Price
    #         "ap": "0.10264410", // Average Price
    #         "sp": "0.10264410", // Stop Price
    #         "x": "NEW", // Execution Type
    #         "X": "NEW", // Order Status
    #         "i": 4293153, // Order Id
    #         "l": "0.00000000", // Order Last Filled Quantity
    #         "z": "0.00000000", // Order Filled Accumulated Quantity
    #         "L": "0.00000000", // Last Filled Price
    #         "N": "USDT", // Commission Asset(Will not push if no commission)
    #         "n": "0", // Commission(Will not push if no commission)
    #         "T": 1499405658657, // Order Trade Time
    #         "t": -1, // Trade Id
    #         "b": 100, // Bids Notional
    #         "a": 100 // Ask Notional
    #         "m": False // Is this trade the maker side?
    #     }
    # }
    # ------------------------------------------------------------------------
    #
    # [Side]
    # BUY
    # SELL
    #
    # [Order Type]
    # MARKET
    # LIMIT
    # STOP
    #
    # [Execution Type]
    # NEW
    # PARTIAL_FILL
    # FILL
    # CANCELED
    # PENDING_CANCEL
    # REJECTED
    # CALCULATED // Liquidation Execution
    # EXPIRED
    # TRADE
    # RESTATED
    #
    # [Order Status]
    # NEW
    # PARTIALLY_FILLED
    # FILLED
    # CANCELED
    # REPLACED
    # PENDING_CANCEL
    # STOPPED
    # REJECTED
    # EXPIRED
    # NEW_INSURANCE // Liquidation with Insurance Fund
    # NEW_ADL // Counterparty Liquidation
    # Time In Force
    #
    # [GTC]
    # IOC
    # FOK
    # GTX
