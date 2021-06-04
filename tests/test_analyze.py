#!/usr/bin/python3

import lakshmi.analyze as analyze
from lakshmi.assets import ManualAsset, TaxLot, TickerAsset
from lakshmi import Account, AssetClass, Portfolio
import unittest
from unittest.mock import patch

class AnalyzeTest(unittest.TestCase):
  def testTLHAnalyzeNoLots(self):
    portfolio = Portfolio(AssetClass('All')).AddAccount(
      Account('Schwab', 'Taxable').AddAsset(
        ManualAsset('Cash', 100.0, {'All' : 1.0})))
    self.assertFalse(
      analyze.TLHAnalyze(0.5, 10000).Analyze(portfolio).List())

  @patch('lakshmi.assets.TickerAsset.Price')
  def testTLHAnalyzePercent(self, mock_price):
    mock_price.return_value = 10.0
    portfolio = Portfolio(AssetClass('All')).AddAccount(
      Account('Schwab', 'Taxable')
      .AddAsset(TickerAsset('VTI', 1000.0, {'All': 1.0}).SetLots(
        [TaxLot('2020/01/31', 500.0, 21.0),
         TaxLot('2021/03/31', 250.0, 14.9),
         TaxLot('2021/05/31', 250.0, 8.0)]))
      .AddAsset(TickerAsset('VXUS', 100.0, {'All': 1.0}).SetLots(
        [TaxLot('2020/01/25', 100.0, 30.0)]))
      .AddAsset(TickerAsset('ITOT', 200.0, {'All': 1.0}).SetLots(
        [TaxLot('2019/09/01', 200.0, 12.0)]))
      .AddAsset(TickerAsset('VOO', 500.0, {'All': 1.0})))
    self.assertListEqual(
      [['Schwab', 'VTI', '2020/01/31', '$5,500.00', '52%'],
       ['Schwab', 'VXUS', '2020/01/25', '$2,000.00', '67%']],
      analyze.TLHAnalyze(0.5).Analyze(portfolio).StrList())

  @patch('lakshmi.assets.TickerAsset.Price')
  def testTLHAnalyzePercentAndDollars(self, mock_price):
    mock_price.return_value = 10.0
    portfolio = Portfolio(AssetClass('All')).AddAccount(
      Account('Schwab', 'Taxable')
      .AddAsset(TickerAsset('VTI', 1000.0, {'All': 1.0}).SetLots(
        [TaxLot('2020/01/31', 500.0, 11.0),
         TaxLot('2021/03/31', 500.0, 12.0)]))
      .AddAsset(TickerAsset('VXUS', 100.0, {'All': 1.0}).SetLots(
        [TaxLot('2020/01/25', 100.0, 30.0)]))
      .AddAsset(TickerAsset('ITOT', 200.0, {'All': 1.0}).SetLots(
        [TaxLot('2019/09/01', 200.0, 12.0)]))
      .AddAsset(TickerAsset('VOO', 500.0, {'All': 1.0})))
    self.assertListEqual(
      [['Schwab', 'VTI', '2020/01/31', '$500.00', '9%'],
       ['Schwab', 'VTI', '2021/03/31', '$1,000.00', '17%'],
       ['Schwab', 'VXUS', '2020/01/25', '$2,000.00', '67%']],
      analyze.TLHAnalyze(0.5, 1400).Analyze(portfolio).StrList())

  def testRebalanceAnalyzeOutsideBounds(self):
    portfolio = Portfolio(
      AssetClass('All')
      .AddSubClass(0.9,
                   AssetClass('Equity')
                   .AddSubClass(0.6, AssetClass('US'))
                   .AddSubClass(0.4, AssetClass('Intl')))
      .AddSubClass(0.1, AssetClass('Bond')).Validate())
    portfolio.AddAccount(
      Account('Schwab', 'Taxable')
      .AddAsset(ManualAsset('Total US', 56.0, {'US': 1.0}))
      .AddAsset(ManualAsset('Total Intl', 30.0, {'Intl': 1.0}))
      .AddAsset(ManualAsset('Total Bond', 14.0, {'Bond': 1.0})))

    self.assertListEqual(
      [['Bond', '14%', '10%', '$14.00', '-$4.00'],
       ['Intl', '30%', '36%', '$30.00', '+$6.00']],
      sorted(analyze.BandRebalance().Analyze(portfolio).StrList()))

  def testRebalanceAnalyzeWithinBounds(self):
    portfolio = Portfolio(
      AssetClass('All')
      .AddSubClass(0.9,
                   AssetClass('Equity')
                   .AddSubClass(0.6, AssetClass('US'))
                   .AddSubClass(0.4, AssetClass('Intl')))
      .AddSubClass(0.1, AssetClass('Bond')).Validate())
    portfolio.AddAccount(
      Account('Schwab', 'Taxable')
      .AddAsset(ManualAsset('Total US', 54.0, {'US': 1.0}))
      .AddAsset(ManualAsset('Total Intl', 35.0, {'Intl': 1.0}))
      .AddAsset(ManualAsset('Total Bond', 11.0, {'Bond': 1.0})))

    self.assertFalse(
      analyze.BandRebalance().Analyze(portfolio).List())


if __name__ == '__main__':
  unittest.main()
