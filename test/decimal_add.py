from random import randrange, uniform
from decimal import Decimal
import unittest

from botfw.etc.util import decimal_add


class TestPreciseAdd(unittest.TestCase):
    '''test class of botfw.etc.util.decimal_add()'''

    def test_integer_add(self):
        min_max = (-1000_000, 1000_000)
        for _ in range(10000):
            x0, x1 = randrange(*min_max), randrange(*min_max)
            ans = x0 + x1
            res = decimal_add(x0, x1)
            self.assertEqual(ans, res)

    def test_float_add(self):
        min_max = (-1000_000_000_000, 1000_000_000_000)
        mul = int(1e8)
        for _ in range(10000):
            x0, x1 = randrange(*min_max), randrange(*min_max)
            ans = x0 + x1
            y0, y1 = float(Decimal(x0) / mul), float(Decimal(x1) / mul)
            res = int(Decimal(str(decimal_add(y0, y1))) * mul)
            self.assertEqual(ans, res)

    def test_float_negative(self):
        for _ in range(100000):
            x = uniform(-1, 1)
            self.assertEqual(x, -float(str(-x)))

            ans = str(x)
            res = str(-x)
            if x > 0:
                self.assertEqual(ans, res[1:])
            else:
                self.assertEqual(ans[1:], res)


if __name__ == "__main__":
    unittest.main()
