from ..base import order as od
from .api import BitbankApi


class BitbankOrderManager(od.OrderManagerBase):
    pass


class BitbankPositionGroup(od.PositionGroupBase):
    pass


class BitbankOrderGroup(od.OrderGroupBase):
    PositionGroup = BitbankPositionGroup


class BitbankOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BitbankOrderGroup
