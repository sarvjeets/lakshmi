"""Tests for lakshmi.assets module."""
import json
import lakshmi.assets as assets
import lakshmi.cache
import pathlib
import unittest
from unittest.mock import MagicMock, patch


class AssetsTest(unittest.TestCase):
  def setUp(self):
    lakshmi.cache.set_cache_dir(None)  # Disable caching.
    self.data_dir = (pathlib.Path(__file__).parent / 'data')

  def testDictManualAssetWithWhatIf(self):
    manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
    manual_asset.WhatIf(100)
    manual_asset = assets.FromDict(assets.ToDict(manual_asset))
    self.assertEqual('Cash', manual_asset.Name())
    self.assertAlmostEqual(100.5, manual_asset.Value())
    self.assertAlmostEqual(200.5, manual_asset.AdjustedValue())
    self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

  def testDictManualAsset(self):
    manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
    manual_asset = assets.FromDict(assets.ToDict(manual_asset))
    self.assertEqual('Cash', manual_asset.Name())
    self.assertAlmostEqual(100.5, manual_asset.AdjustedValue())
    self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

  @patch('yfinance.Ticker')
  def testBadTicker(self, MockTicker):
    bad_ticker = MagicMock()
    bad_ticker.info = {}
    MockTicker.return_value = bad_ticker

    ticker_asset = assets.TickerAsset('bad', 10, {'All': 1.0})

    with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
      ticker_asset.Name()
    with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
      ticker_asset.Value()

    MockTicker.assert_called_once_with('bad')

  @patch('yfinance.Ticker')
  def testGoodTicker(self, MockTicker):
    ticker = MagicMock()
    ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                   'regularMarketPrice': 1.0}
    MockTicker.return_value = ticker

    vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
    self.assertAlmostEqual(100.0, vmmxx.Value())
    self.assertEqual('Vanguard Cash Reserves Federal', vmmxx.Name())
    self.assertEqual('VMMXX', vmmxx.ShortName())

    MockTicker.assert_called_once_with('VMMXX')

  @patch('yfinance.Ticker')
  def testTaxLotsTicker(self, MockTicker):
    ticker = MagicMock()
    ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                   'regularMarketPrice': 1.0}
    MockTicker.return_value = ticker

    vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
    lots = [assets.TaxLot('2012/12/12', 50, 1.0),
            assets.TaxLot('2013/12/12', 30, 0.9)]
    with self.assertRaisesRegex(AssertionError,
                                'Lots provided should sum up to 100.0'):
      vmmxx.SetLots(lots)

    lots.append(assets.TaxLot('2014/12/31', 20, 0.9))
    vmmxx.SetLots(lots)
    self.assertListEqual(lots, vmmxx.tax_lots)

  @patch('yfinance.Ticker')
  def testDictTicker(self, MockTicker):
    ticker = MagicMock()
    ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                   'regularMarketPrice': 1.0}
    MockTicker.return_value = ticker

    vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
    lots = [assets.TaxLot('2012/12/12', 50, 1.0),
            assets.TaxLot('2013/12/12', 50, 0.9)]
    vmmxx.SetLots(lots)
    vmmxx.WhatIf(-10)
    vmmxx = assets.FromDict(assets.ToDict(vmmxx))
    self.assertEqual('VMMXX', vmmxx.ticker)
    self.assertEqual(100.0, vmmxx.shares)
    self.assertEqual({'All': 1.0}, vmmxx.class2ratio)
    self.assertAlmostEqual(90.0, vmmxx.AdjustedValue())
    self.assertEqual(2, len(vmmxx.tax_lots))

  @patch('requests.get')
  def testVanguardFundsName(self, MockGet):
    MockReq = MagicMock()

    with open(self.data_dir / 'profile.json') as data_file:
      MockReq.json.return_value = json.load(data_file)

    MockGet.return_value = MockReq

    fund = assets.VanguardFund(7555, 10, {'All': 1.0})
    self.assertEqual('Vanguard Institutional Total Bond Market Index Trust',
                     fund.Name())
    self.assertEqual('7555', fund.ShortName())
    MockGet.assert_called_once_with(
      'https://api.vanguard.com/rs/ire/01/pe/fund/7555/profile.json',
      headers={'Referer': 'https://vanguard.com/'})

  @patch('requests.get')
  def testVanguardFundsValue(self, MockGet):
    MockReq = MagicMock()

    with open(self.data_dir / 'price.json') as data_file:
      MockReq.json.return_value = json.load(data_file)
    MockGet.return_value = MockReq

    fund = assets.VanguardFund(7555, 10, {'All': 1.0})
    self.assertEqual(1166.6, fund.Value())
    MockGet.assert_called_once_with(
      'https://api.vanguard.com/rs/ire/01/pe/fund/7555/price.json',
      headers={'Referer': 'https://vanguard.com/'})
    fund.SetLots([assets.TaxLot('2012/12/30', 10, 1.0)])

  def testDictVanguardFund(self):
    fund = assets.VanguardFund(1234, 20, {'Bonds': 1.0})
    fund.SetLots([assets.TaxLot('2021/05/15', 20, 5.0)])
    fund.WhatIf(100)
    fund = assets.FromDict(assets.ToDict(fund))
    self.assertEqual(1234, fund.fund_id)
    self.assertEqual(20, fund.shares)
    self.assertEqual({'Bonds': 1.0}, fund.class2ratio)
    self.assertEqual(1, len(fund.tax_lots))
    self.assertEqual(100, fund._delta)

  @patch('datetime.datetime')
  @patch('requests.post')
  def testIBonds(self, MockPost, MockDate):
    MockReq = MagicMock()
    with open(self.data_dir / 'SBCPrice-I.html') as html_file:
      MockReq.text = html_file.read()
    MockPost.return_value = MockReq
    MockDate.now.strftime.return_value = '04/2021'

    ibonds = assets.IBonds({'All': 1.0})
    ibonds.AddBond('03/2020', 10000)

    MockPost.asset_called_once_with(
      'http://www.treasurydirect.gov/BC/SBCPrice',
      data = {
        'RedemptionDate' : '04/2021',
        'Series' : 'I',
        'Denomination' : '1000',
        'IssueDate' : '03/2020',
        'btnAdd.x' : 'CALCULATE'})

    self.assertEqual('I Bonds', ibonds.Name())
    self.assertEqual('I Bonds', ibonds.ShortName())
    self.assertAlmostEqual(10156.0, ibonds.Value())
    self.assertEqual(1, len(ibonds.ListBonds()))
    self.assertEqual(4, len(ibonds.ListBonds()[0]))
    self.assertEqual('03/2020', ibonds.ListBonds()[0][0])
    self.assertEqual(10000, ibonds.ListBonds()[0][1])
    self.assertEqual('1.88%', ibonds.ListBonds()[0][2])
    self.assertAlmostEqual(10156.0, ibonds.ListBonds()[0][3])

  def testDictIBonds(self):
    ibonds = assets.IBonds({'B': 1.0})
    ibonds.AddBond('02/2020', 10000)
    ibonds.WhatIf(-100.0)
    ibonds = assets.FromDict(assets.ToDict(ibonds))
    self.assertEqual('I Bonds', ibonds.Name())
    self.assertEqual({'B': 1.0}, ibonds.class2ratio)
    self.assertAlmostEqual(-100.0, ibonds._delta)
    self.assertEqual(1, len(ibonds.bonds))

  @patch('datetime.datetime')
  @patch('requests.post')
  def testEEBonds(self, MockPost, MockDate):
    MockReq = MagicMock()
    with open(self.data_dir / 'SBCPrice-EE.html') as html_file:
      MockReq.text = html_file.read()
    MockPost.return_value = MockReq
    MockDate.now.strftime.return_value = '04/2021'

    eebonds = assets.EEBonds({'All': 1.0})
    eebonds.AddBond('03/2020', 10000)

    MockPost.asset_called_once_with(
      'http://www.treasurydirect.gov/BC/SBCPrice',
      data = {
        'RedemptionDate' : '04/2021',
        'Series' : 'EE',
        'Denomination' : '500',
        'IssueDate' : '03/2020',
        'btnAdd.x' : 'CALCULATE'})

    self.assertEqual('EE Bonds', eebonds.Name())
    self.assertEqual('EE Bonds', eebonds.ShortName())
    self.assertAlmostEqual(10008.0, eebonds.Value())
    self.assertEqual(1, len(eebonds.ListBonds()))
    self.assertEqual(4, len(eebonds.ListBonds()[0]))
    self.assertEqual('03/2020', eebonds.ListBonds()[0][0])
    self.assertEqual(10000, eebonds.ListBonds()[0][1])
    self.assertEqual('0.10%', eebonds.ListBonds()[0][2])
    self.assertAlmostEqual(10008.0, eebonds.ListBonds()[0][3])

  def testDictEEBonds(self):
    eebonds = assets.EEBonds({'B': 1.0})
    eebonds.AddBond('02/2020', 10000)
    eebonds.WhatIf(-100.0)
    eebonds = assets.FromDict(assets.ToDict(eebonds))
    self.assertEqual('EE Bonds', eebonds.Name())
    self.assertEqual({'B': 1.0}, eebonds.class2ratio)
    self.assertAlmostEqual(-100.0, eebonds._delta)
    self.assertEqual(1, len(eebonds.bonds))


if __name__ == '__main__':
  unittest.main()
