#!/usr/bin/python3

import assets

import unittest

class TestTicker():
  def __init__(self, name, price):
    self.info = {'shortName': name, 'regularMarketPrice': price}

  def Ticker(self, name):
    return self


class AssetsTest(unittest.TestCase):
  def test_BadTicker(self):
    bad_ticker_class = TestTicker(None, None)
    with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
      assets.TickerAsset('bad', 10, {}, ticker_obj=bad_ticker_class.Ticker)

  def test_GoodTicker(self):
    ticker_obj = TestTicker('Vanguard Cash Reserves Federal', 1.0)
    vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0},
                               ticker_obj=ticker_obj.Ticker)
    self.assertAlmostEqual(100.0, vmmxx.Value())
    self.assertEqual('Vanguard Cash Reserves Federal', vmmxx.Name())

if __name__ == '__main__':
  unittest.main()
