"""Tests for lakshmi.assets module."""
import unittest
from unittest.mock import patch

import lakshmi.analyze as analyze
from lakshmi import Account, AssetClass, Portfolio
from lakshmi.assets import ManualAsset, TaxLot, TickerAsset


class AnalyzeTest(unittest.TestCase):
    def test_tlh_no_lots(self):
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable').add_asset(
                ManualAsset('Cash', 100.0, {'All': 1.0})))
        self.assertListEqual(
            [],
            analyze.TLH(0.5, 10000).analyze(portfolio).list())

    @patch('lakshmi.assets.TickerAsset.price')
    def test_tlh_loss_percent(self, mock_price):
        mock_price.return_value = 10.0
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable')
            .add_asset(TickerAsset('VTI', 1000.0, {'All': 1.0}).set_lots(
                [TaxLot('2020/01/31', 500.0, 21.0),
                 TaxLot('2021/03/31', 250.0, 14.9),
                 TaxLot('2021/05/31', 250.0, 8.0)]))
            .add_asset(TickerAsset('VXUS', 100.0, {'All': 1.0}).set_lots(
                [TaxLot('2020/01/25', 100.0, 30.0)]))
            .add_asset(TickerAsset('ITOT', 200.0, {'All': 1.0}).set_lots(
                [TaxLot('2019/09/01', 200.0, 12.0)]))
            .add_asset(TickerAsset('VOO', 500.0, {'All': 1.0})))
        self.assertListEqual(
            [['Schwab', 'VTI', '2020/01/31', '$5,500.00', '52%'],
             ['Schwab', 'VXUS', '2020/01/25', '$2,000.00', '67%']],
            analyze.TLH(0.5).analyze(portfolio).str_list())

    @patch('lakshmi.assets.TickerAsset.price')
    def test_tlh_combo(self, mock_price):
        mock_price.return_value = 10.0
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable')
            .add_asset(TickerAsset('VTI', 1000.0, {'All': 1.0}).set_lots(
                [TaxLot('2020/01/31', 500.0, 11.0),
                 TaxLot('2021/03/31', 500.0, 12.0)]))
            .add_asset(TickerAsset('VXUS', 100.0, {'All': 1.0}).set_lots(
                [TaxLot('2020/01/25', 100.0, 30.0)]))
            .add_asset(TickerAsset('ITOT', 200.0, {'All': 1.0}).set_lots(
                [TaxLot('2019/09/01', 200.0, 12.0)]))
            .add_asset(TickerAsset('VOO', 500.0, {'All': 1.0})))
        self.assertListEqual(
            [['Schwab', 'VTI', '2020/01/31', '$500.00', '9%'],
             ['Schwab', 'VTI', '2021/03/31', '$1,000.00', '17%'],
             ['Schwab', 'VXUS', '2020/01/25', '$2,000.00', '67%']],
            analyze.TLH(0.5, 1400).analyze(portfolio).str_list())

    def test_rebalance_outside_bounds(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 56.0, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 30.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 14.0, {'Bond': 1.0})))

        self.assertListEqual(
            [['Bond', '14%', '10%', '$14.00', '-$4.00'],
             ['Intl', '30%', '36%', '$30.00', '+$6.00']],
            sorted(analyze.BandRebalance().analyze(portfolio).str_list()))

    def test_rebalance_within_bounds(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 54.0, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 35.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 11.0, {'Bond': 1.0})))

        self.assertListEqual(
            [],
            analyze.BandRebalance().analyze(portfolio).list())


if __name__ == '__main__':
    unittest.main()
