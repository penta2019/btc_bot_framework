# ポジションサイズがQuote通貨(法定通貨)で表現される場合の損益計算。
# 例：bitmex(USD)

from botfw.base.order import PositionGroupBase


class PositionGroup(PositionGroupBase):
    INVERSE = True


pos = PositionGroup()  # price(USD) size(USD)


def update(p, s):
    pos.update(p, s)
    print(f'price:{p}, size:{s}')
    print(pos)
    print()


# pnlはUSD表記。MEX公式はBTC表記なので注意
update(10000, +10000)  # 10000USD 10000USDロング (10000/10000 BTC)
update(12000, -10000)  # 12000USD 10000USD利確   (10000/12000 BTC)
# BTCの差額が利益: pnl = (10000/10000 - 10000/12000) BTC
#                    = (10000/10000 - 10000/12000) * 12000 USD = 2000 USD

update(10000, +10000)  # 10000USDロング
update(12000, -20000)  # 10000USDロング利確, 10000USDショート
update(10000, +10000)  # 10000USDショート利確

# 注: positon = 0 の時は計算の都合上 average_price = 1 となる
# 注: sizeの+はインデントを揃えるためなので不要
