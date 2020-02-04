from .api_ccxt import CcxtGmocoinApi
from ..base.api import ApiBase


class GmocoinApi(ApiBase, CcxtGmocoinApi):
    MAX_API_CAPACITY = 1
    API_PER_SECOND = 1
    _ccxt_class = CcxtGmocoinApi

    def __init__(self, ccxt_config={}):
        ApiBase.__init__(self)
        CcxtGmocoinApi.__init__(self, ccxt_config)
        self.load_markets()

    def fetch_status(self, params=None):
        pass

    def fetch_position(self, symbol):
        pass

    def fetch_collateral(self):
        pass

    def websocket_key(self, method='POST', key=None):
        # POST: create new (valid for 60 minutes)
        # PUT: keep alive (require key)
        # DELETE: close (require key)
        params = {'token': key} if key else {}
        res = self.request('ws-auth', 'private', method, params)
        return res
