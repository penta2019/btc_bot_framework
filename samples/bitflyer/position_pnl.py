# bitflyerの様にポジションサイズをBTCで計算する場合のサンプル

from botfw.base.order import PositionGroupBase


class PositionGroup(PositionGroupBase):
    SIZE_IN_FIAT = False  # デフォルトでFalseなので書かなくても良い


pos = PositionGroup()  # price(JPY) size(BTC)


def update(p, s):
    pos.update(p, s)
    print(f'price:{p}, size:{s}')
    print(pos)
    print()


update(800000, +1)  # 80万円 1BTCロング
update(820000, +1)  # 82万円 1BTC買い増し
update(830000, -3)  # 83万円 ロング2BTC利確、1BTCドテンショート
update(800000, +2)  # 80万円 ショート1BTC利確、1BTCドテン買い
update(810000, -1)  # 81万円 1BTCロング利確

# 注: position = 0 の時は計算の都合上 average_price = 1 となる
# 注: sizeの+はインデントを揃えるためなので不要
