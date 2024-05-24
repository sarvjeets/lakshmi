"""Tests for lakshmi module."""
import unittest
from unittest.mock import patch

import lakshmi.cache
from lakshmi import Account, AssetClass, Portfolio
from lakshmi.assets import ManualAsset, TaxLot, TickerAsset
from lakshmi.table import Table


class LakshmiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lakshmi.cache.set_cache_dir(None)  # Disable caching.

    def test_empty_portfolio(self):
        portfolio = Portfolio(AssetClass('E'))
        self.assertAlmostEqual(0, portfolio.total_value())
        self.assertListEqual([], portfolio.list_assets().list())
        self.assertListEqual([], portfolio.asset_location().list())
        self.assertListEqual([], portfolio.asset_allocation_tree().list())
        self.assertListEqual([], portfolio.asset_allocation([]).list())
        self.assertListEqual([], portfolio.asset_allocation_compact().list())
        self.assertListEqual([], portfolio.list_lots().list())

    def test_one_asset_class(self):
        AssetClass('Equity').validate()

    def test_many_asset_class_duplicate(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('International')))
            .add_subclass(0.2, AssetClass('US')))
        with self.assertRaisesRegex(AssertionError, 'Found duplicate'):
            asset_class.validate()

    def test_many_asset_class_bad_ratio_sum(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.5, AssetClass('International')))
            .add_subclass(0.2, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Sum of sub-classes'):
            asset_class.validate()

    def test_many_asset_class_bad_ratio_neg(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(-0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('International')))
            .add_subclass(0.2, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Bad ratio'):
            asset_class.validate()

    def test_many_asset_class_bad_ratio_high(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(1.5,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('International')))
            .add_subclass(0.2, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Bad ratio'):
            asset_class.validate()

    def test_many_asset_class(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('International')))
            .add_subclass(0.2, AssetClass('Bonds'))).validate()

        self.assertEqual(
            {'US', 'International', 'Bonds'},
            asset_class.leaves())

        ret_class, ratio = asset_class.find_asset_class('All')
        self.assertEqual('All', ret_class.name)
        self.assertAlmostEqual(1.0, ratio)
        ret_class, ratio = asset_class.find_asset_class('Equity')
        self.assertEqual('Equity', ret_class.name)
        self.assertAlmostEqual(0.8, ratio)
        ret_class, ratio = asset_class.find_asset_class('US')
        self.assertEqual('US', ret_class.name)
        self.assertAlmostEqual(0.48, ratio)
        ret_class, ratio = asset_class.find_asset_class('International')
        self.assertEqual('International', ret_class.name)
        self.assertAlmostEqual(0.32, ratio)
        ret_class, ratio = asset_class.find_asset_class('Bonds')
        self.assertEqual('Bonds', ret_class.name)
        self.assertAlmostEqual(0.2, ratio)

    def test_asset_class_dict(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('International')))
            .add_subclass(0.2, AssetClass('Bonds'))).validate()

        asset_class = AssetClass.from_dict(asset_class.to_dict())
        self.assertEqual(
            {'US', 'International', 'Bonds'},
            asset_class.leaves())
        ret_class, ratio = asset_class.find_asset_class('US')
        self.assertEqual('US', ret_class.name)
        self.assertAlmostEqual(0.48, ratio)

    def test_asset_class_copy(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('International')))
            .add_subclass(0.2, AssetClass('Bonds'))).validate()

        asset_class2 = asset_class.copy().validate()
        asset_class2.name = 'Changed'
        self.assertEqual('All', asset_class.name)

    def test_value_mapped(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.6, AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.4, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Need to validate'):
            asset_class.value_mapped({})

        asset_class.validate()
        money_allocation = {
            'US': 10.0,
            'Intl': 20.0,
            'Bonds': 40.0,
            'Unused': 50.0}

        self.assertAlmostEqual(
            70.0, asset_class.value_mapped(money_allocation))
        self.assertAlmostEqual(
            30.0, asset_class.children()[0][0].value_mapped(money_allocation))
        self.assertAlmostEqual(
            40.0, asset_class.children()[1][0].value_mapped(money_allocation))

    def test_bad_asset(self):
        portfolio = Portfolio(AssetClass('Equity'))
        account = Account('Roth IRA', 'Post-tax').add_asset(
            ManualAsset('Test Asset', 100.0, {'Bad Equity': 1.0}))
        with self.assertRaisesRegex(
                AssertionError,
                'Unknown or non-leaf asset class: Bad Equity'):
            portfolio.add_account(account)

    def test_get_set_assets_from_account(self):
        account = (Account('Roth IRA', 'Post-tax')
                   .add_asset(ManualAsset('Test 1', 100.0, {'All': 1.0}))
                   .add_asset(ManualAsset('Test 2', 200.0, {'All': 1.0})))
        asset = account.get_asset('Test 1')
        self.assertEqual('Test 1', asset.name())
        self.assertAlmostEqual(100.0, asset.value())

        account.add_asset(ManualAsset('Test 1', 300.0, {'All': 1.0}),
                          replace=True)
        account.set_assets(account.assets())
        self.assertEqual(2, len(account.assets()))
        account.remove_asset('Test 1')
        with self.assertRaises(KeyError):
            account.get_asset('Test 1')

    def test_account_dict(self):
        account = Account('Roth IRA', 'Post-tax').add_asset(
            ManualAsset('Test Asset', 100.0, {'All': 1.0}))
        account.add_cash(200)
        account = Account.from_dict(account.to_dict())
        self.assertEqual(1, len(account._assets))
        self.assertEqual('Test Asset', account.get_asset('Test Asset').name())
        self.assertAlmostEqual(200.0, account.available_cash())

    def test_account_string(self):
        account = Account('Roth IRA', 'Post-tax').add_asset(
            ManualAsset('Test', 100.0, {'All': 1.0}))
        expected = (Table(2)
                    .add_row(['Name:', 'Roth IRA'])
                    .add_row(['Type:', 'Post-tax'])
                    .add_row(['Total:', '$100.00']))
        self.assertEqual(expected.string(tablefmt='plain'), account.string())

        account.add_cash(-10)
        expected.add_row(['Available Cash:', '-$10.00'])
        self.assertEqual(expected.string(tablefmt='plain'), account.string())

    def test_duplicate_account(self):
        portfolio = Portfolio(AssetClass('All'))
        account = Account('Roth IRA', 'Post-tax').add_asset(
            ManualAsset('Test Asset', 100.0, {'All': 1.0}))
        portfolio.add_account(account)
        with self.assertRaisesRegex(AssertionError, 'Attempting to add'):
            portfolio.add_account(account)
        portfolio.add_account(account, replace=True)

    def test_remove_account(self):
        portfolio = Portfolio(AssetClass('All'))
        account = Account('Roth IRA', 'Post-tax').add_asset(
            ManualAsset('Test Asset', 100.0, {'All': 1.0}))
        portfolio.add_account(account)
        portfolio.remove_account('Roth IRA')
        self.assertEqual(0, len(portfolio.accounts()))

    def test_one_asset(self):
        portfolio = Portfolio(AssetClass('Equity')).add_account(
            Account('401(k)', 'Pre-tax').add_asset(
                ManualAsset('Test Asset', 100.0, {'Equity': 1.0})))

        self.assertEqual(1, len(portfolio.accounts()))
        self.assertListEqual([['401(k)', 'Test Asset', '$100.00']],
                             portfolio.list_assets().str_list())
        self.assertAlmostEqual(100.0, portfolio.total_value())
        self.assertListEqual([['Equity', 'Pre-tax', '100.0%', '$100.00']],
                             portfolio.asset_location().str_list())
        self.assertListEqual([], portfolio.asset_allocation_tree().list())
        self.assertListEqual(
            [['Equity', '100.0%', '100.0%', '$100.00', '+$0.00']],
            portfolio.asset_allocation(['Equity']).str_list())
        self.assertListEqual([], portfolio.asset_allocation_tree().list())
        self.assertListEqual([], portfolio.asset_allocation_compact().list())

    def test_portfolio_dict(self):
        portfolio = Portfolio(AssetClass('Equity')).add_account(
            Account('401(k)', 'Pre-tax').add_asset(
                ManualAsset('Test Asset', 100.0, {'Equity': 1.0})))
        portfolio = Portfolio.from_dict(portfolio.to_dict())
        self.assertEqual(1, len(portfolio.accounts()))

    def test_asset_what_if(self):
        asset = ManualAsset('Test Asset', 100.0, {'Equity': 1.0})
        self.assertAlmostEqual(100, asset.adjusted_value())
        asset.what_if(-10.0)
        self.assertAlmostEqual(100, asset.value())
        self.assertAlmostEqual(90, asset.adjusted_value())
        asset.what_if(10)
        self.assertAlmostEqual(100, asset.adjusted_value())

    def test_one_asset_two_class(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.5, AssetClass('Equity'))
            .add_subclass(0.5, AssetClass('Fixed Income'))).add_account(
            Account('Vanguard', 'Taxable').add_asset(
                ManualAsset('Test Asset', 100.0,
                            {'Equity': 0.6, 'Fixed Income': 0.4})))

        self.assertListEqual([['Vanguard', 'Test Asset', '$100.00']],
                             portfolio.list_assets().str_list())
        self.assertAlmostEqual(100.0, portfolio.total_value())
        self.assertListEqual(
            [['Equity', 'Taxable', '100.0%', '$60.00'],
             ['Fixed Income', 'Taxable', '100.0%', '$40.00']],
            portfolio.asset_location().str_list())

        self.assertListEqual(
            [['All:'],
             ['Equity', '60.0%', '50.0%', '$60.00'],
                ['Fixed Income', '40.0%', '50.0%', '$40.00']],
            portfolio.asset_allocation_tree().str_list())
        self.assertListEqual(
            [['Equity', '60.0%', '50.0%', '$60.00', '-$10.00'],
             ['Fixed Income', '40.0%', '50.0%', '$40.00', '+$10.00']],
            portfolio.asset_allocation(['Equity', 'Fixed Income']).str_list())
        self.assertListEqual([
            ['Equity', '60%', '50%', '60.0%', '50.0%', '$60.00', '-$10.00'],
            ['Fixed Income', '40%', '50%', '40.0%', '50.0%', '$40.00',
             '+$10.00']],
            portfolio.asset_allocation_compact().str_list())

    def test_list_accounts_no_money(self):
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable'))

        self.assertListEqual(
            [['Schwab', 'Taxable', '$0.00']],
            portfolio.list_accounts().str_list())
        self.assertListEqual(
            [['Taxable', '$0.00']],
            portfolio.list_accounts(group_by_type=True).str_list())

    def test_list_accounts(self):
        portfolio = (Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable').add_asset(
                ManualAsset('Fund', 100.0, {'All': 1.0})))
            .add_account(Account('Vanguard', 'Taxable').add_asset(
                ManualAsset('Fund', 50.0, {'All': 1.0})))
            .add_account(Account('Fidelity', '401K').add_asset(
                ManualAsset('F', 50.0, {'All': 1.0}))))

        self.assertListEqual(
            [['Schwab', 'Taxable', '$100.00', '50.0%'],
             ['Vanguard', 'Taxable', '$50.00', '25.0%'],
             ['Fidelity', '401K', '$50.00', '25.0%']],
            portfolio.list_accounts().str_list())
        self.assertListEqual(
            [['Taxable', '$150.00', '75.0%'],
             ['401K', '$50.00', '25.0%']],
            portfolio.list_accounts(group_by_type=True).str_list())

    @patch('lakshmi.assets.TickerAsset.name')
    @patch('lakshmi.assets.TickerAsset.price')
    def test_list_assets(self, mock_price, mock_name):
        mock_price.return_value = 1.0
        mock_name.return_value = 'Vanguard Cash Reserves Federal'

        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable')
            .add_asset(TickerAsset('VMMXX', 420.0, {'All': 1.0}))
            .add_asset(ManualAsset('Cash', 840.0, {'All': 1.0})))

        self.assertListEqual(
            [['Schwab', 'Vanguard Cash Reserves Federal', '$420.00'],
             ['Schwab', 'Cash', '$840.00']],
            portfolio.list_assets().str_list())
        self.assertListEqual(
            [['Schwab', 'VMMXX', 'Vanguard Cash Reserves Federal', '$420.00'],
             ['Schwab', 'Cash', 'Cash', '$840.00']],
            portfolio.list_assets(short_name=True).str_list())
        self.assertListEqual(
            [['Schwab', 'VMMXX', '420.0', 'Vanguard Cash Reserves Federal',
              '$420.00'],
             ['Schwab', 'Cash', '', 'Cash', '$840.00']],
            portfolio.list_assets(short_name=True, quantity=True).str_list())
        self.assertListEqual(
            [['Schwab', '420.0', 'Vanguard Cash Reserves Federal', '$420.00'],
             ['Schwab', '', 'Cash', '$840.00']],
            portfolio.list_assets(quantity=True).str_list())
        self.assertListEqual(
            [['Schwab', 'VMMXX', '$420.00'],
             ['Schwab', 'Cash', '$840.00']],
            portfolio.list_assets(short_name=True, long_name=False).str_list())

    def test_asset_location(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.2, AssetClass('Bonds')).validate())
        (portfolio
         .add_account(Account('Account1', 'Taxable')
                      .add_asset(ManualAsset('US A', 60.0, {'US': 1.0}))
                      .add_asset(ManualAsset('Intl A', 30.0, {'Intl': 1.0}))
                      .add_asset(ManualAsset('Bond A', 10.0, {'Bonds': 1.0})))
         .add_account(Account('Account2', 'Pre-tax')
                      .add_asset(ManualAsset('Bond A', 40.0, {'Bonds': 1.0}))))
        self.assertEqual(
            [['US', 'Taxable', '100.0%', '$60.00'],
             ['Intl', 'Taxable', '100.0%', '$30.00'],
             ['Bonds', 'Pre-tax', '80.0%', '$40.00'],
             ['', 'Taxable', '20.0%', '$10.00']],
            portfolio.asset_location().str_list())

    def test_flat_asset_allocation(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.2, AssetClass('Bonds')).validate()).add_account(
            Account('Account', 'Taxable')
            .add_asset(ManualAsset('US Asset', 60.0, {'US': 1.0}))
            .add_asset(ManualAsset('Intl Asset', 30.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Bond Asset', 10.0, {'Bonds': 1.0})))

        with self.assertRaisesRegex(AssertionError,
                                    'AssetAllocation called with'):
            portfolio.asset_allocation(['Equity', 'Intl'])

        self.assertListEqual(
            [['US', '60.0%', '48.0%', '$60.00', '-$12.00'],
             ['Intl', '30.0%', '32.0%', '$30.00', '+$2.00'],
             ['Bonds', '10.0%', '20.0%', '$10.00', '+$10.00']],
            portfolio.asset_allocation(['US', 'Intl', 'Bonds']).str_list())
        self.assertListEqual(
            [['Equity', '90.0%', '80.0%', '$90.00', '-$10.00'],
             ['Bonds', '10.0%', '20.0%', '$10.00', '+$10.00']],
            portfolio.asset_allocation(['Equity', 'Bonds']).str_list())

    def test_asset_allocation_compact(self):
        portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.8,
                          AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.2, AssetClass('Bonds')).validate()).add_account(
            Account('Account', 'Taxable')
            .add_asset(ManualAsset('US Asset', 60.0, {'US': 1.0}))
            .add_asset(ManualAsset('Intl Asset', 30.0, {'Intl': 1.0}))
            .add_asset(ManualAsset('Bond Asset', 10.0, {'Bonds': 1.0})))

        self.assertListEqual(
            [['Equity', '90%', '80%', 'US', '67%', '60%', '60.0%', '48.0%',
              '$60.00', '-$12.00'],
             ['', '', '', 'Intl', '33%', '40%', '30.0%', '32.0%',
              '$30.00', '+$2.00'],
             ['Bonds', '10%', '20%', '', '', '', '10.0%', '20.0%',
              '$10.00', '+$10.00']],
            portfolio.asset_allocation_compact().str_list())
        self.assertListEqual(
            [['All:'],
             ['Equity', '90.0%', '80.0%', '$90.00'],
             ['Bonds', '10.0%', '20.0%', '$10.00'],
             [' '],
             ['Equity:'],
             ['US', '66.7%', '60.0%', '$60.00'],
             ['Intl', '33.3%', '40.0%', '$30.00']],
            portfolio.asset_allocation_tree().str_list())

    def test_multiple_accounts_and_assets(self):
        portfolio = Portfolio(AssetClass('All'))
        asset_class_map = {'All': 1.0}
        (portfolio
         .add_account(
             Account('Account 1', 'Taxable')
             .add_asset(ManualAsset('Asset 1', 100.0, asset_class_map))
             .add_asset(ManualAsset('Asset 2', 200.0, asset_class_map)))
         .add_account(
             Account('Account 2', 'Roth IRA')
             .add_asset(ManualAsset('Asset 1', 300.0, asset_class_map))
             .add_asset(ManualAsset('Asset 2', 400.0, asset_class_map))))

        self.assertAlmostEqual(1000.0, portfolio.total_value())
        self.assertEqual(
            'Account 1',
            portfolio.get_account('Account 1').name())
        self.assertEqual(
            'Account 2',
            portfolio.get_account('Account 2').name())
        self.assertAlmostEqual(
            100.0,
            portfolio.get_account('Account 1').get_asset('Asset 1').value())
        self.assertAlmostEqual(
            200.0,
            portfolio.get_account('Account 1').get_asset('Asset 2').value())
        self.assertAlmostEqual(
            300.0,
            portfolio.get_account('Account 2').get_asset('Asset 1').value())
        self.assertAlmostEqual(
            400.0,
            portfolio.get_account('Account 2').get_asset('Asset 2').value())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '$100.00'],
             ['Account 1', 'Asset 2', '$200.00'],
             ['Account 2', 'Asset 1', '$300.00'],
             ['Account 2', 'Asset 2', '$400.00']],
            portfolio.list_assets().str_list())

    def test_get_account_name_by_substr(self):
        portfolio = Portfolio(AssetClass('All'))
        asset_class_map = {'All': 1.0}
        (portfolio
         .add_account(
             Account('Account 1', 'Taxable')
             .add_asset(ManualAsset('Asset 1', 100.0, asset_class_map))
             .add_asset(ManualAsset('Asset 2', 200.0, asset_class_map)))
         .add_account(
             Account('Account 2', 'Roth IRA')
             .add_asset(ManualAsset('Asset 1', 300.0, asset_class_map))
             .add_asset(ManualAsset('Asset 2', 400.0, asset_class_map))))
        self.assertEqual(
            'Account 1',
            portfolio.get_account_name_by_substr('1'))
        with self.assertRaisesRegex(AssertionError, 'matches more than'):
            portfolio.get_account_name_by_substr('Acc')
        with self.assertRaisesRegex(AssertionError, 'does not match'):
            portfolio.get_account_name_by_substr('God')

    def test_get_asset_name_by_substr(self):
        portfolio = Portfolio(AssetClass('All'))
        asset_class_map = {'All': 1.0}
        (portfolio
         .add_account(
             Account('Account 1', 'Taxable')
             .add_asset(ManualAsset('Asset 1', 100.0, asset_class_map))
             .add_asset(ManualAsset('Asset 2', 200.0, asset_class_map)))
         .add_account(
             Account('Account 2', 'Roth IRA')
             .add_asset(ManualAsset('Asset 1', 300.0, asset_class_map))
             .add_asset(ManualAsset('Funky Asset', 400.0, asset_class_map))))
        self.assertTupleEqual(('Account 2', 'Asset 1'),
                              portfolio.get_asset_name_by_substr(
            account_str='2', asset_str='1'))
        self.assertAlmostEqual(('Account 1', 'Asset 2'),
                               portfolio.get_asset_name_by_substr(
            account_str='Account', asset_str='2'))
        self.assertAlmostEqual(('Account 1', 'Asset 1'),
                               portfolio.get_asset_name_by_substr(
            account_str='1', asset_str='Asset 1'))
        self.assertAlmostEqual(('Account 2', 'Funky Asset'),
                               portfolio.get_asset_name_by_substr(
            asset_str='Funky'))

        with self.assertRaisesRegex(AssertionError, 'more than one'):
            portfolio.get_asset_name_by_substr(
                account_str='Acc', asset_str='Ass')
        with self.assertRaisesRegex(AssertionError, 'match none of'):
            portfolio.get_asset_name_by_substr(
                account_str='1', asset_str='Funky')
        with self.assertRaisesRegex(AssertionError, 'match none of'):
            portfolio.get_asset_name_by_substr(
                account_str='Acc', asset_str='Yolo')

    def test_what_ifs(self):
        portfolio = Portfolio(AssetClass('All')
                              .add_subclass(0.6, AssetClass('Equity'))
                              .add_subclass(0.4, AssetClass('Bonds')))
        asset1 = ManualAsset('Asset 1', 100.0, {'Equity': 1.0})
        asset2 = ManualAsset('Asset 2', 100.0, {'Bonds': 1.0})
        account1 = Account('Account 1', 'Taxable')
        account1.add_asset(asset1).add_asset(asset2)
        account2 = Account('Account 2', 'Pre-tax')
        portfolio.add_account(account1).add_account(account2)

        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual([], account_whatifs.list())
        self.assertListEqual([], asset_whatifs.list())

        portfolio.what_if('Account 1', 'Asset 2', -20)
        self.assertAlmostEqual(80, asset2.adjusted_value())
        self.assertAlmostEqual(20, account1.available_cash())
        self.assertAlmostEqual(200, portfolio.total_value())
        self.assertAlmostEqual(200, portfolio.total_value(False))
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual([['Account 1', '+$20.00']],
                             account_whatifs.str_list())
        self.assertListEqual([['Account 1', 'Asset 2', '-$20.00']],
                             asset_whatifs.str_list())

        portfolio.what_if('Account 1', 'Asset 1', 20)
        self.assertAlmostEqual(120, asset1.adjusted_value())
        self.assertAlmostEqual(0, account1.available_cash())
        self.assertAlmostEqual(200, portfolio.total_value())
        self.assertAlmostEqual(200, portfolio.total_value(False))
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual([], account_whatifs.str_list())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '+$20.00'],
             ['Account 1', 'Asset 2', '-$20.00']],
            asset_whatifs.str_list())

        self.assertListEqual(
            [['Account 1', 'Asset 1', '$120.00'],
             ['Account 1', 'Asset 2', '$80.00']],
            portfolio.list_assets().str_list())

        self.assertListEqual(
            [['All:'],
             ['Equity', '60.0%', '60.0%', '$120.00'],
             ['Bonds', '40.0%', '40.0%', '$80.00']],
            portfolio.asset_allocation_tree().str_list())

        portfolio.what_if_add_cash('Account 1', 30)
        self.assertAlmostEqual(30, account1.available_cash())
        self.assertAlmostEqual(230, portfolio.total_value())
        self.assertAlmostEqual(200, portfolio.total_value(False))
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual(
            [['Account 1', '+$30.00']],
            account_whatifs.str_list())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '+$20.00'],
             ['Account 1', 'Asset 2', '-$20.00']],
            asset_whatifs.str_list())

        portfolio.what_if_add_cash('Account 2', 460)
        self.assertAlmostEqual(460, account2.available_cash())
        self.assertAlmostEqual(690, portfolio.total_value())
        self.assertAlmostEqual(200, portfolio.total_value(False))
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual(
            [['Account 1', '+$30.00'],
             ['Account 2', '+$460.00']],
            account_whatifs.str_list())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '+$20.00'],
             ['Account 1', 'Asset 2', '-$20.00']],
            asset_whatifs.str_list())

        self.assertListEqual(
            [['Equity', 'Taxable', '100.0%', '$120.00'],
             ['Bonds', 'Taxable', '100.0%', '$80.00']],
            portfolio.asset_location().str_list())

        portfolio.reset_what_ifs()
        self.assertAlmostEqual(100, asset1.adjusted_value())
        self.assertAlmostEqual(100, asset2.adjusted_value())
        self.assertAlmostEqual(0, account1.available_cash())
        self.assertAlmostEqual(0, account2.available_cash())
        self.assertAlmostEqual(200, portfolio.total_value())
        self.assertAlmostEqual(200, portfolio.total_value(False))
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual([], account_whatifs.str_list())
        self.assertListEqual([], asset_whatifs.str_list())

    @patch('lakshmi.assets.TickerAsset.name')
    @patch('lakshmi.assets.TickerAsset.price')
    def test_get_what_ifs_options(self, mock_price, mock_name):
        mock_price.return_value = 2.0
        mock_name.return_value = 'Vanguard Cash Reserves Federal'

        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable')
            .add_asset(TickerAsset('VMMXX', 420.0, {'All': 1.0}))
            .add_asset(ManualAsset('Cash', 840.0, {'All': 1.0})))

        portfolio.what_if('Schwab', 'VMMXX', -20)
        portfolio.what_if('Schwab', 'Cash', 20)
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual(
            [['Schwab', 'Vanguard Cash Reserves Federal', '-$20.00'],
             ['Schwab', 'Cash', '+$20.00']],
            asset_whatifs.str_list())
        account_whatifs, asset_whatifs = portfolio.get_what_ifs(
            long_name=False, short_name=True)
        self.assertListEqual(
            [['Schwab', 'VMMXX', '-$20.00'],
             ['Schwab', 'Cash', '+$20.00']],
            asset_whatifs.str_list())
        account_whatifs, asset_whatifs = portfolio.get_what_ifs(
            long_name=False, short_name=True, quantity=True)
        self.assertListEqual(
            [['Schwab', 'VMMXX', '-10', '-$20.00'],
             ['Schwab', 'Cash', '', '+$20.00']],
            asset_whatifs.str_list())

    def test_what_ifs_double_add(self):
        portfolio = Portfolio(AssetClass('All'))

        asset = ManualAsset('Asset', 100.0, {'All': 1.0})
        account = Account('Account', 'Taxable')
        portfolio.add_account(account.add_asset(asset))

        portfolio.what_if('Account', 'Asset', 20)
        portfolio.what_if('Account', 'Asset', 30)
        self.assertAlmostEqual(150, asset.adjusted_value())
        self.assertAlmostEqual(-50, account.available_cash())
        self.assertAlmostEqual(100, portfolio.total_value())
        account_whatifs, asset_whatifs = portfolio.get_what_ifs()
        self.assertListEqual(
            [['Account', '-$50.00']],
            account_whatifs.str_list())
        self.assertListEqual(
            [['Account', 'Asset', '+$50.00']],
            asset_whatifs.str_list())

    def test_return_allocation_one_asset(self):
        asset_class = AssetClass('All').validate()
        allocation = {'All': 10.0}

        ret = asset_class.return_allocation(allocation)
        self.assertEqual(1, len(ret))
        self.assertEqual('All', ret[0].name)
        self.assertAlmostEqual(10.0, ret[0].value)
        self.assertEqual([], ret[0].children)

    def test_return_allocation_asset_tree(self):
        asset_class = (
            AssetClass('All')
            .add_subclass(0.6, AssetClass('Equity')
                          .add_subclass(0.6, AssetClass('US'))
                          .add_subclass(0.4, AssetClass('Intl')))
            .add_subclass(0.4, AssetClass('Bonds'))).validate()
        allocation = {'US': 10.0, 'Intl': 20.0, 'Bonds': 40.0}

        ret = asset_class.return_allocation(allocation, levels=0)

        self.assertEqual(1, len(ret))
        self.assertEqual('All', ret[0].name)
        self.assertAlmostEqual(70.0, ret[0].value)

        self.assertEqual(2, len(ret[0].children))
        self.assertEqual('Equity', ret[0].children[0].name)
        self.assertAlmostEqual(
            0.429, ret[0].children[0].actual_allocation, places=3)
        self.assertAlmostEqual(0.6, ret[0].children[0].desired_allocation)
        self.assertAlmostEqual(12.0, ret[0].children[0].value_difference)
        self.assertEqual('Bonds', ret[0].children[1].name)
        self.assertAlmostEqual(
            0.571, ret[0].children[1].actual_allocation, places=3)
        self.assertAlmostEqual(0.4, ret[0].children[1].desired_allocation)
        self.assertAlmostEqual(-12.0, ret[0].children[1].value_difference)

        self.assertEqual(
            3, len(
                asset_class.return_allocation(
                    allocation, levels=1)))
        self.assertEqual(
            5, len(
                asset_class.return_allocation(
                    allocation, levels=2)))
        self.assertEqual(5, len(asset_class.return_allocation(allocation)))
        self.assertEqual(
            5, len(
                asset_class.return_allocation(
                    allocation, levels=5)))

    @patch('lakshmi.assets.TickerAsset.name')
    @patch('lakshmi.assets.TickerAsset.price')
    def test_list_lots(self, mock_price, mock_name):
        mock_price.return_value = 200.0
        mock_name.return_value = 'Unused'

        vti = TickerAsset('VTI', 100.0, {'All': 1.0})
        vti.set_lots([TaxLot('2020/01/01', 50, 100.0),
                      TaxLot('2021/01/01', 50, 300.0)])
        vxus = TickerAsset('VXUS', 50.0, {'All': 1.0})
        vxus.set_lots([TaxLot('2019/01/01', 50, 150.0)])
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable')
            .add_asset(vti)
            .add_asset(ManualAsset('Cash', 840.0, {'All': 1.0}))
            .add_asset(vxus))
        # Order of lots: ShortName, Date, Cost, Gain, Gain%
        self.assertListEqual(
            [['VTI', '2020/01/01', '$5,000.00', '+$5,000.00', '100.0%'],
             ['VTI', '2021/01/01', '$15,000.00', '-$5,000.00', '-33.3%'],
             ['VXUS', '2019/01/01', '$7,500.00', '+$2,500.00', '33.3%']],
            portfolio.list_lots().str_list())

    @patch('lakshmi.assets.TickerAsset.name')
    @patch('lakshmi.assets.TickerAsset.price')
    def test_list_lots_with_account_and_term(self, mock_price, mock_name):
        mock_price.return_value = 200.0
        mock_name.return_value = 'Unused'

        vti = TickerAsset('VTI', 100.0, {'All': 1.0})
        vti.set_lots([TaxLot('2020/01/01', 50, 100.0),
                      TaxLot('2021/01/01', 50, 300.0)])
        vxus = TickerAsset('VXUS', 50.0, {'All': 1.0})
        vxus.set_lots([TaxLot('2019/01/01', 50, 150.0)])
        portfolio = Portfolio(AssetClass('All')).add_account(
            Account('Schwab', 'Taxable')
            .add_asset(vti)
            .add_asset(ManualAsset('Cash', 840.0, {'All': 1.0}))
            .add_asset(vxus))
        # Order of lots: Account, ShortName, Date, Cost, Gain, Gain%
        self.assertListEqual(
            [['Schwab', 'VTI', '2020/01/01', '$5,000.00', '+$5,000.00',
              '100.0%'],
             ['Schwab', 'VTI', '2021/01/01', '$15,000.00', '-$5,000.00',
              '-33.3%'],
             ['Schwab', 'VXUS', '2019/01/01', '$7,500.00', '+$2,500.00',
              '33.3%']],
            portfolio.list_lots(include_account=True).str_list())

        # We just check that term is included in the row instead of exact
        # calculatin of term
        self.assertListEqual(
            [6, 6, 6],
            list(map(len, portfolio.list_lots(include_term=True).list())))
        self.assertListEqual(
            [7, 7, 7],
            list(map(len, portfolio.list_lots(
                include_account=True, include_term=True).list())))


if __name__ == '__main__':
    unittest.main()
