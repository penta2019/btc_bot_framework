from ..base.trade import TradeBase
from .websocket import BitbankWebsocket
from .api import BitbankApi
from ..etc.util import unix_time_from_ISO8601Z


class BitbankTrade(TradeBase):
    pass
