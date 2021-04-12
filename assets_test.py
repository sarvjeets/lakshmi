#!/usr/bin/python3

import assets

import unittest

class AssetsTest(unittest.TestCase):
  def test_BadTicker(self):
    self.assertRaisesRegex(Exception, 'Cannot retrieve ticker',
                           assets.TickerAsset, 'bad', 10, {})

  def test_GoodTicker(self):
    vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})

    self.assertEqual(100.0, vmmxx.Value())
    self.assertEqual('Vanguard Cash Reserves Federal', vmmxx.Name())

if __name__ == '__main__':
  unittest.main()
