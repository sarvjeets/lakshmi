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

    def test_allocate_no_cash(self):
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable').add_asset(
                ManualAsset('Cash', 100.0, {'All': 1.0})))
        with self.assertRaisesRegex(AssertionError, 'No available cash'):
            analyze.Allocate('Schwab').analyze(portfolio)

    def test_allocate_not_enough_assets(self):
        account = Account('Schwab', 'Taxable').add_asset(
            ManualAsset('Cash', 100.0, {'All': 1.0}))
        account.add_cash(-200)
        portfolio = Portfolio(AssetClass('All')).add_account(account)
        with self.assertRaisesRegex(AssertionError, 'Cash to withdraw'):
            analyze.Allocate('Schwab').analyze(portfolio)

    def test_allocate_not_enough_assets_blacklisted(self):
        account = (
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Cash', 100.0, {'All': 1.0}))
            .add_asset(ManualAsset('Black Cash', 100.0, {'All': 1.0})))
        account.add_cash(-150)
        portfolio = Portfolio(AssetClass('All')).add_account(account)
        with self.assertRaisesRegex(AssertionError, 'Cash to withdraw'):
            analyze.Allocate(
                'Schwab', exclude_assets=['Black Cash']).analyze(portfolio)

    def test_allocate_no_assets(self):
        account = Account('Schwab', 'Taxable').add_asset(
            ManualAsset('Cash', 100.0, {'All': 1.0}))
        account.add_cash(200)
        portfolio = Portfolio(AssetClass('All')).add_account(account)
        with self.assertRaisesRegex(AssertionError, 'No assets to allocate'):
            analyze.Allocate('Schwab', ['Cash']).analyze(portfolio)

    def test_allocate_one_assets(self):
        account = Account('Schwab', 'Taxable').add_asset(
            ManualAsset('Cash', 100.0, {'All': 1.0}))
        account.add_cash(200)
        portfolio = Portfolio(AssetClass('All')).add_account(account)
        self.assertListEqual(
            [['Cash', '+$200.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())

    def test_allocate_cash(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 53.0, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 35.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 9.0, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(3)
        self.assertListEqual(
            [['Total US', '+$1.00'],
             ['Total Intl', '+$1.00'],
             ['Total Bond', '+$1.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())
        self.assertAlmostEqual(
            54, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            36, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

        account.add_cash(100)
        self.assertListEqual(
            [['Total US', '+$54.00'],
             ['Total Intl', '+$36.00'],
             ['Total Bond', '+$10.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())
        self.assertAlmostEqual(
            54 * 2, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            36 * 2, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10 * 2, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

        account.add_cash(-200)
        self.assertListEqual(
            [['Total US', '-$108.00'],
             ['Total Intl', '-$72.00'],
             ['Total Bond', '-$20.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())
        self.assertAlmostEqual(
            0, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            0, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            0, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_cash_indentical_assets(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 53.0, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 17.5, {'Intl': 1.0}))
            .add_asset(ManualAsset('Ex US', 17.5, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 9.0, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(3)
        self.assertListEqual(
            [['Total US', '+$1.00'],
             ['Total Intl', '+$0.50'],
             ['Ex US', '+$0.50'],
             ['Total Bond', '+$1.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())

    def test_allocate_cash_overlapping_assets(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4,
                                        AssetClass('Intl')
                                        .add_subclass(
                                            0.7, AssetClass('Developed'))
                                        .add_subclass(
                                            0.3, AssetClass('Emerging'))))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 53.0, {'US': 1.0}))
            .add_asset(ManualAsset('Intl', 17.5, {'Developed': 0.7,
                                                  'Emerging': 0.3}))
            .add_asset(ManualAsset('Devel', 12.25, {'Developed': 1.0}))
            .add_asset(ManualAsset('Emer', 5.25, {'Emerging': 1.0}))
            .add_asset(ManualAsset('Total Bond', 9.0, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(3)
        self.assertListEqual(
            [['Total US', '+$1.00'],
             ['Intl', '+$0.33'],
             ['Devel', '+$0.47'],
             ['Emer', '+$0.20'],
             ['Total Bond', '+$1.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())

    def test_allocate_only_rebalance(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 60.0, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 40.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 0, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        self.assertListEqual(
            [['Total US', '-$6.00'],
             ['Total Intl', '-$4.00'],
             ['Total Bond', '+$10.00']],
            analyze.Allocate('Schwab', rebalance=True).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            54, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            36, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_cash_rebalance(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 50.0, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 40.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 0, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(10)
        self.assertListEqual(
            [['Total US', '+$4.00'],
             ['Total Intl', '-$4.00'],
             ['Total Bond', '+$10.00']],
            analyze.Allocate('Schwab', rebalance=True).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            54, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            36, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_cash_large_portfolio(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 53e6, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 35e6, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 9e6, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(3e6)
        self.assertListEqual(
            [['Total US', '+$1,000,000.00'],
             ['Total Intl', '+$1,000,000.00'],
             ['Total Bond', '+$1,000,000.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())
        self.assertAlmostEqual(
            54e6, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            36e6, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10e6, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_cash_rebalance_large_portfolio(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 50e6, {'US': 1.0}))
            .add_asset(ManualAsset('Total Intl', 40e6, {'Intl': 1.0}))
            .add_asset(ManualAsset('Total Bond', 0, {'Bond': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(10e6)
        self.assertListEqual(
            [['Total US', '+$4,000,000.00'],
             ['Total Intl', '-$4,000,000.00'],
             ['Total Bond', '+$10,000,000.00']],
            analyze.Allocate('Schwab', rebalance=True).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            54e6, account.get_asset('Total US').adjusted_value(), places=6)
        self.assertAlmostEqual(
            36e6, account.get_asset('Total Intl').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10e6, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_cash_going_negative_corr(self):
        # In this test case, due to coorelation between funds, the solution
        # will drive Developed/emerging funds to negative balance.
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4,
                                        AssetClass('Intl')
                                        .add_subclass(
                                            0.7, AssetClass('Developed'))
                                        .add_subclass(
                                            0.3, AssetClass('Emerging'))))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 54.0, {'US': 1.0}))
            .add_asset(ManualAsset('Intl', 16.2, {'Developed': 0.7,
                                                  'Emerging': 0.3}))
            .add_asset(ManualAsset('Devel', 11.34, {'Developed': 1.0}))
            .add_asset(ManualAsset('Emer', 4.86, {'Emerging': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10.0, {'Bond': 1.0})))

        portfolio.get_account('Schwab').add_cash(3)
        self.assertListEqual(
            [['Total US', '+$0.00'],
             ['Intl', '+$0.98'],
             ['Devel', '+$1.36'],
             ['Emer', '+$0.66'],
             ['Total Bond', '+$0.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())

    def test_allocate_cash_going_positive_corr(self):
        # In this test case, due to coorelation between funds, the solution
        # will drive Developed/emerging funds to positive balance.
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4,
                                        AssetClass('Intl')
                                        .add_subclass(
                                            0.7, AssetClass('Developed'))
                                        .add_subclass(
                                            0.3, AssetClass('Emerging'))))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total US', 54.0, {'US': 1.0}))
            .add_asset(ManualAsset('Intl', 19.8, {'Developed': 0.7,
                                                  'Emerging': 0.3}))
            .add_asset(ManualAsset('Devel', 13.86, {'Developed': 1.0}))
            .add_asset(ManualAsset('Emer', 5.94, {'Emerging': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10.0, {'Bond': 1.0})))

        portfolio.get_account('Schwab').add_cash(-3)
        self.assertListEqual(
            [['Total US', '+$0.00'],
             ['Intl', '-$0.98'],
             ['Devel', '-$1.36'],
             ['Emer', '-$0.66'],
             ['Total Bond', '+$0.00']],
            analyze.Allocate('Schwab').analyze(portfolio).str_list())

    def test_allocate_cash_withdrawing_more(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9, AssetClass('Equity'))
            .add_subclass(0.1, AssetClass('Bond')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('US', 90, {'Equity': 1.0}))
            .add_asset(ManualAsset('Bonds', 20, {'Bond': 1.0})))
        portfolio.add_account(
            Account('401K', 'Tax-Deferred')
            .add_asset(ManualAsset('US', 3, {'Equity': 1.0}))
            .add_asset(ManualAsset('Bonds', 1, {'Bond': 1.0})))

        portfolio.get_account('401K').add_cash(-2)

        # We should ideally withdraw money from bonds, but it doesn't have
        # any balance to withdraw.
        self.assertListEqual(
            [['US', '-$1.00'],
             ['Bonds', '-$1.00']],
            analyze.Allocate('401K').analyze(portfolio).str_list())

    def test_allocate_zero_ratio(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9, AssetClass('Equity'))
            .add_subclass(0.1, AssetClass('Bond'))
            .add_subclass(0, AssetClass('Zero')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total Market', 90.0, {'Equity': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10, {'Bond': 1.0}))
            .add_asset(ManualAsset('Total Zero', 10, {'Zero': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(10)
        # These numbers "look" incorrect, but one can manually verify that the
        # defined error function is minimized at this point.
        self.assertListEqual(
            [['Total Market', '+$8.12'],
             ['Total Bond', '+$1.88'],
             ['Total Zero', '+$0.00']],
            analyze.Allocate('Schwab', rebalance=False).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            98.12, account.get_asset('Total Market').adjusted_value(),
            places=2)
        self.assertAlmostEqual(
            11.88, account.get_asset('Total Bond').adjusted_value(), places=2)
        self.assertAlmostEqual(
            10, account.get_asset('Total Zero').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_zero_ratio_withdraw(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9, AssetClass('Equity'))
            .add_subclass(0.1, AssetClass('Bond'))
            .add_subclass(0, AssetClass('Zero')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total Market', 90.0, {'Equity': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10, {'Bond': 1.0}))
            .add_asset(ManualAsset('Total Zero', 10, {'Zero': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(-10)
        self.assertListEqual(
            [['Total Market', '+$0.00'],
             ['Total Bond', '+$0.00'],
             ['Total Zero', '-$10.00']],
            analyze.Allocate('Schwab', rebalance=False).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            90, account.get_asset('Total Market').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(
            0, account.get_asset('Total Zero').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_zero_ratio_withdraw_less(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9, AssetClass('Equity'))
            .add_subclass(0.1, AssetClass('Bond'))
            .add_subclass(0, AssetClass('Zero')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total Market', 90.0, {'Equity': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10, {'Bond': 1.0}))
            .add_asset(ManualAsset('Total Zero', 10, {'Zero': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(-5)
        self.assertListEqual(
            [['Total Market', '+$0.00'],
             ['Total Bond', '+$0.00'],
             ['Total Zero', '-$5.00']],
            analyze.Allocate('Schwab', rebalance=False).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            90, account.get_asset('Total Market').adjusted_value(), places=6)
        self.assertAlmostEqual(
            10, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(
            5, account.get_asset('Total Zero').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_zero_ratio_withdraw_more(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9, AssetClass('Equity'))
            .add_subclass(0.1, AssetClass('Bond'))
            .add_subclass(0, AssetClass('Zero')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total Market', 90.0, {'Equity': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10, {'Bond': 1.0}))
            .add_asset(ManualAsset('Total Zero', 10, {'Zero': 1.0})))

        account = portfolio.get_account('Schwab')
        account.add_cash(-20)
        self.assertListEqual(
            [['Total Market', '-$9.00'],
             ['Total Bond', '-$1.00'],
             ['Total Zero', '-$10.00']],
            analyze.Allocate('Schwab', rebalance=False).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            81, account.get_asset('Total Market').adjusted_value(), places=6)
        self.assertAlmostEqual(
            9, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(
            0, account.get_asset('Total Zero').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)

    def test_allocate_zero_ratio_rebalance(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.9, AssetClass('Equity'))
            .add_subclass(0.1, AssetClass('Bond'))
            .add_subclass(0, AssetClass('Zero')).validate())
        portfolio.add_account(
            Account('Schwab', 'Taxable')
            .add_asset(ManualAsset('Total Market', 90.0, {'Equity': 1.0}))
            .add_asset(ManualAsset('Total Bond', 10, {'Bond': 1.0}))
            .add_asset(ManualAsset('Total Zero', 10, {'Zero': 1.0})))

        account = portfolio.get_account('Schwab')
        self.assertListEqual(
            [['Total Market', '+$9.00'],
             ['Total Bond', '+$1.00'],
             ['Total Zero', '-$10.00']],
            analyze.Allocate('Schwab', rebalance=True).analyze(
                portfolio).str_list())
        self.assertAlmostEqual(
            99, account.get_asset('Total Market').adjusted_value(), places=6)
        self.assertAlmostEqual(
            11, account.get_asset('Total Bond').adjusted_value(), places=6)
        self.assertAlmostEqual(
            0, account.get_asset('Total Zero').adjusted_value(), places=6)
        self.assertAlmostEqual(0, account.available_cash(), places=6)


if __name__ == '__main__':
    unittest.main()
