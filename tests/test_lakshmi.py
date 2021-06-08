"""Tests for lakshmi module."""
from lakshmi import Account, AssetClass, Portfolio
from lakshmi.assets import ManualAsset
import unittest


class LakshmiTest(unittest.TestCase):
    def testEmptyPortfolio(self):
        portfolio = Portfolio(AssetClass('E'))
        self.assertAlmostEqual(0, portfolio.TotalValue())
        self.assertListEqual([], portfolio.Assets().List())
        self.assertListEqual([], portfolio.AssetLocation().List())
        self.assertListEqual([], portfolio.AssetAllocationTree().List())
        self.assertListEqual([], portfolio.AssetAllocation([]).List())
        self.assertListEqual([], portfolio.AssetAllocationCompact().List())

    def testOneAssetClass(self):
        asset_class = AssetClass('Equity').Validate()

    def testManyAssetClassDuplicate(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('US')))
        with self.assertRaisesRegex(AssertionError, 'Found duplicate'):
            asset_class.Validate()

    def testManyAssetClassBadRatioSum(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.5, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Sum of sub-classes'):
            asset_class.Validate()

    def testManyAssetClassBadRatioNeg(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(-0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Bad ratio'):
            asset_class.Validate()

    def testManyAssetClassBadRatioHigh(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(1.5,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Bad ratio'):
            asset_class.Validate()

    def testManyAssetClass(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('Bonds'))).Validate()

        self.assertEqual(
            {'US', 'International', 'Bonds'},
            asset_class.Leaves())

        ret_class, ratio = asset_class.FindAssetClass('All')
        self.assertEqual('All', ret_class.name)
        self.assertAlmostEqual(1.0, ratio)
        ret_class, ratio = asset_class.FindAssetClass('Equity')
        self.assertEqual('Equity', ret_class.name)
        self.assertAlmostEqual(0.8, ratio)
        ret_class, ratio = asset_class.FindAssetClass('US')
        self.assertEqual('US', ret_class.name)
        self.assertAlmostEqual(0.48, ratio)
        ret_class, ratio = asset_class.FindAssetClass('International')
        self.assertEqual('International', ret_class.name)
        self.assertAlmostEqual(0.32, ratio)
        ret_class, ratio = asset_class.FindAssetClass('Bonds')
        self.assertEqual('Bonds', ret_class.name)
        self.assertAlmostEqual(0.2, ratio)

    def testAssetClassDict(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('Bonds'))).Validate()

        asset_class = AssetClass.FromDict(asset_class.ToDict())
        self.assertEqual(
            {'US', 'International', 'Bonds'},
            asset_class.Leaves())
        ret_class, ratio = asset_class.FindAssetClass('US')
        self.assertEqual('US', ret_class.name)
        self.assertAlmostEqual(0.48, ratio)

    def testAssetClassCopy(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('International')))
            .AddSubClass(0.2, AssetClass('Bonds'))).Validate()

        asset_class2 = asset_class.Copy().Validate()
        asset_class2.name = 'Changed'
        self.assertEqual('All', asset_class.name)

    def testValueMapped(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.6, AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('Intl')))
            .AddSubClass(0.4, AssetClass('Bonds')))

        with self.assertRaisesRegex(AssertionError, 'Need to validate'):
            asset_class.ValueMapped({})

        asset_class.Validate()
        money_allocation = {
            'US': 10.0,
            'Intl': 20.0,
            'Bonds': 40.0,
            'Unused': 50.0}

        self.assertAlmostEqual(70.0, asset_class.ValueMapped(money_allocation))
        self.assertAlmostEqual(
            30.0, asset_class.children[0][0].ValueMapped(money_allocation))
        self.assertAlmostEqual(
            40.0, asset_class.children[1][0].ValueMapped(money_allocation))

    def testBadAsset(self):
        portfolio = Portfolio(AssetClass('Equity'))
        account = Account('Roth IRA', 'Post-tax').AddAsset(
            ManualAsset('Test Asset', 100.0, {'Bad Equity': 1.0}))
        with self.assertRaisesRegex(AssertionError,
                                    'Unknown or non-leaf asset class: Bad Equity'):
            portfolio.AddAccount(account)

    def testDuplicateAccount(self):
        portfolio = Portfolio(AssetClass('All'))
        account = Account('Roth IRA', 'Post-tax').AddAsset(
            ManualAsset('Test Asset', 100.0, {'All': 1.0}))
        portfolio.AddAccount(account)
        with self.assertRaisesRegex(AssertionError, 'Attempting to add'):
            portfolio.AddAccount(account)

    def testGetAssetFromAccount(self):
        account = Account('Roth IRA', 'Post-tax').AddAsset(
            ManualAsset('Test Asset', 100.0, {'All': 1.0}))
        asset = account.GetAsset('Test Asset')
        self.assertEqual('Test Asset', asset.Name())
        self.assertAlmostEqual(100.0, asset.Value())

    def testAccountDict(self):
        account = Account('Roth IRA', 'Post-tax').AddAsset(
            ManualAsset('Test Asset', 100.0, {'All': 1.0}))
        account.AddCash(200)
        account = Account.FromDict(account.ToDict())
        self.assertEqual(1, len(account._assets))
        self.assertEqual('Test Asset', account.GetAsset('Test Asset').Name())
        self.assertAlmostEqual(200.0, account.AvailableCash())

    def testOneAsset(self):
        portfolio = Portfolio(AssetClass('Equity')).AddAccount(
            Account('401(k)', 'Pre-tax').AddAsset(
                ManualAsset('Test Asset', 100.0, {'Equity': 1.0})))

        self.assertEqual(1, len(portfolio.Accounts()))
        self.assertListEqual([['401(k)', 'Test Asset', '$100.00']],
                             portfolio.Assets().StrList())
        self.assertAlmostEqual(100.0, portfolio.TotalValue())
        self.assertListEqual([['Pre-tax', '$100.00', '100%']],
                             portfolio.AssetLocation().StrList())
        self.assertListEqual([], portfolio.AssetAllocationTree().List())
        self.assertListEqual(
            [['Equity', '100%', '100%', '$100.00', '+$0.00']],
            portfolio.AssetAllocation(['Equity']).StrList())
        self.assertListEqual([], portfolio.AssetAllocationTree().List())
        self.assertListEqual([], portfolio.AssetAllocationCompact().List())

    def testPortfolioDict(self):
        portfolio = Portfolio(AssetClass('Equity')).AddAccount(
            Account('401(k)', 'Pre-tax').AddAsset(
                ManualAsset('Test Asset', 100.0, {'Equity': 1.0})))
        portfolio = Portfolio.FromDict(portfolio.ToDict())
        self.assertEqual(1, len(portfolio.Accounts()))

    def testAssetWhatIf(self):
        asset = ManualAsset('Test Asset', 100.0, {'Equity': 1.0})
        self.assertAlmostEqual(100, asset.AdjustedValue())
        asset.WhatIf(-10.0)
        self.assertAlmostEqual(100, asset.Value())
        self.assertAlmostEqual(90, asset.AdjustedValue())
        asset.WhatIf(10)
        self.assertAlmostEqual(100, asset.AdjustedValue())

    def testOneAssetTwoClass(self):
        portfolio = Portfolio(
            AssetClass('All')
            .AddSubClass(0.5, AssetClass('Equity'))
            .AddSubClass(0.5, AssetClass('Fixed Income'))).AddAccount(
            Account('Vanguard', 'Taxable').AddAsset(
                ManualAsset('Test Asset', 100.0,
                            {'Equity': 0.6, 'Fixed Income': 0.4})))

        self.assertListEqual([['Vanguard', 'Test Asset', '$100.00']],
                             portfolio.Assets().StrList())
        self.assertAlmostEqual(100.0, portfolio.TotalValue())
        self.assertListEqual([['Taxable', '$100.00', '100%']],
                             portfolio.AssetLocation().StrList())

        self.assertListEqual(
            [['All:'],
             ['Equity', '60%', '50%', '$60.00'],
                ['Fixed Income', '40%', '50%', '$40.00']],
            portfolio.AssetAllocationTree().StrList())
        self.assertListEqual(
            [['Equity', '60%', '50%', '$60.00', '-$10.00'],
             ['Fixed Income', '40%', '50%', '$40.00', '+$10.00']],
            portfolio.AssetAllocation(['Equity', 'Fixed Income']).StrList())
        self.assertListEqual(
            [['Equity', '60%', '50%', '60%', '50%', '$60.00', '-$10.00'],
             ['Fixed Income', '40%', '50%', '40%', '50%', '$40.00', '+$10.00']],
            portfolio.AssetAllocationCompact().StrList())

    def testFlatAssetAllocation(self):
        portfolio = Portfolio(
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('Intl')))
            .AddSubClass(0.2, AssetClass('Bonds')).Validate()).AddAccount(
            Account('Account', 'Taxable')
            .AddAsset(ManualAsset('US Asset', 60.0, {'US': 1.0}))
            .AddAsset(ManualAsset('Intl Asset', 30.0, {'Intl': 1.0}))
            .AddAsset(ManualAsset('Bond Asset', 10.0, {'Bonds': 1.0})))

        with self.assertRaisesRegex(AssertionError,
                                    'AssetAllocation called with'):
            portfolio.AssetAllocation(['Equity', 'Intl'])

        self.assertListEqual(
            [['US', '60%', '48%', '$60.00', '-$12.00'],
             ['Intl', '30%', '32%', '$30.00', '+$2.00'],
                ['Bonds', '10%', '20%', '$10.00', '+$10.00']],
            portfolio.AssetAllocation(['US', 'Intl', 'Bonds']).StrList())
        self.assertListEqual(
            [['Equity', '90%', '80%', '$90.00', '-$10.00'],
             ['Bonds', '10%', '20%', '$10.00', '+$10.00']],
            portfolio.AssetAllocation(['Equity', 'Bonds']).StrList())

    def testAssetAllocationCompact(self):
        portfolio = Portfolio(
            AssetClass('All')
            .AddSubClass(0.8,
                         AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('Intl')))
            .AddSubClass(0.2, AssetClass('Bonds')).Validate()).AddAccount(
            Account('Account', 'Taxable')
            .AddAsset(ManualAsset('US Asset', 60.0, {'US': 1.0}))
            .AddAsset(ManualAsset('Intl Asset', 30.0, {'Intl': 1.0}))
            .AddAsset(ManualAsset('Bond Asset', 10.0, {'Bonds': 1.0})))

        self.assertListEqual(
            [['Equity', '90%', '80%', 'US', '67%', '60%', '60%', '48%', '$60.00', '-$12.00'],
             ['', '', '', 'Intl', '33%', '40%', '30%', '32%', '$30.00', '+$2.00'],
                ['Bonds', '10%', '20%', '', '', '', '10%', '20%', '$10.00', '+$10.00']],
            portfolio.AssetAllocationCompact().StrList())

    def testMultipleAccountsAndAssets(self):
        portfolio = Portfolio(AssetClass('All'))
        asset_class_map = {'All': 1.0}
        (portfolio
         .AddAccount(
             Account('Account 1', 'Taxable')
             .AddAsset(ManualAsset('Asset 1', 100.0, asset_class_map))
             .AddAsset(ManualAsset('Asset 2', 200.0, asset_class_map)))
         .AddAccount(
             Account('Account 2', 'Roth IRA')
             .AddAsset(ManualAsset('Asset 1', 300.0, asset_class_map))
             .AddAsset(ManualAsset('Asset 2', 400.0, asset_class_map))))

        self.assertAlmostEqual(1000.0, portfolio.TotalValue())
        self.assertEqual('Account 1', portfolio.GetAccount('Account 1').Name())
        self.assertEqual('Account 2', portfolio.GetAccount('Account 2').Name())
        self.assertEqual(
            100.0,
            portfolio.GetAccount('Account 1').GetAsset('Asset 1').Value())
        self.assertEqual(
            200.0,
            portfolio.GetAccount('Account 1').GetAsset('Asset 2').Value())
        self.assertEqual(
            300.0,
            portfolio.GetAccount('Account 2').GetAsset('Asset 1').Value())
        self.assertEqual(
            400.0,
            portfolio.GetAccount('Account 2').GetAsset('Asset 2').Value())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '$100.00'],
             ['Account 1', 'Asset 2', '$200.00'],
                ['Account 2', 'Asset 1', '$300.00'],
                ['Account 2', 'Asset 2', '$400.00']],
            portfolio.Assets().StrList())

    def testWhatIfs(self):
        portfolio = Portfolio(AssetClass('All')
                              .AddSubClass(0.6, AssetClass('Equity'))
                              .AddSubClass(0.4, AssetClass('Bonds')))
        asset1 = ManualAsset('Asset 1', 100.0, {'Equity': 1.0})
        asset2 = ManualAsset('Asset 2', 100.0, {'Bonds': 1.0})
        account1 = Account('Account 1', 'Taxable')
        account1.AddAsset(asset1).AddAsset(asset2)
        account2 = Account('Account 2', 'Pre-tax')
        portfolio.AddAccount(account1).AddAccount(account2)

        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual([], account_whatifs.List())
        self.assertListEqual([], asset_whatifs.List())

        portfolio.WhatIf('Account 1', 'Asset 2', -20)
        self.assertAlmostEqual(80, asset2.AdjustedValue())
        self.assertAlmostEqual(20, account1.AvailableCash())
        self.assertAlmostEqual(200, portfolio.TotalValue())
        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual([['Account 1', '+$20.00']],
                             account_whatifs.StrList())
        self.assertListEqual([['Account 1', 'Asset 2', '-$20.00']],
                             asset_whatifs.StrList())

        portfolio.WhatIf('Account 1', 'Asset 1', 20)
        self.assertAlmostEqual(120, asset1.AdjustedValue())
        self.assertAlmostEqual(0, account1.AvailableCash())
        self.assertAlmostEqual(200, portfolio.TotalValue())
        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual([], account_whatifs.StrList())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '+$20.00'],
             ['Account 1', 'Asset 2', '-$20.00']],
            asset_whatifs.StrList())

        self.assertListEqual(
            [['Account 1', 'Asset 1', '$120.00'],
             ['Account 1', 'Asset 2', '$80.00']],
            portfolio.Assets().StrList())

        self.assertListEqual(
            [['All:'],
             ['Equity', '60%', '60%', '$120.00'],
                ['Bonds', '40%', '40%', '$80.00']],
            portfolio.AssetAllocationTree().StrList())

        portfolio.WhatIfAddCash('Account 1', 30)
        self.assertAlmostEqual(30, account1.AvailableCash())
        self.assertAlmostEqual(230, portfolio.TotalValue())
        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual(
            [['Account 1', '+$30.00']],
            account_whatifs.StrList())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '+$20.00'],
             ['Account 1', 'Asset 2', '-$20.00']],
            asset_whatifs.StrList())

        portfolio.WhatIfAddCash('Account 2', 460)
        self.assertAlmostEqual(460, account2.AvailableCash())
        self.assertAlmostEqual(690, portfolio.TotalValue())
        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual(
            [['Account 1', '+$30.00'],
             ['Account 2', '+$460.00']],
            account_whatifs.StrList())
        self.assertListEqual(
            [['Account 1', 'Asset 1', '+$20.00'],
             ['Account 1', 'Asset 2', '-$20.00']],
            asset_whatifs.StrList())

        self.assertListEqual(
            [['Taxable', '$230.00', '33%'],
             ['Pre-tax', '$460.00', '67%']],
            portfolio.AssetLocation().StrList())

        portfolio.ResetWhatIfs()
        self.assertAlmostEqual(100, asset1.AdjustedValue())
        self.assertAlmostEqual(100, asset2.AdjustedValue())
        self.assertAlmostEqual(0, account1.AvailableCash())
        self.assertAlmostEqual(0, account2.AvailableCash())
        self.assertAlmostEqual(200, portfolio.TotalValue())
        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual([], account_whatifs.StrList())
        self.assertListEqual([], asset_whatifs.StrList())

    def testWhatIfsDoubleAdd(self):
        portfolio = Portfolio(AssetClass('All'))

        asset = ManualAsset('Asset', 100.0, {'All': 1.0})
        account = Account('Account', 'Taxable')
        portfolio.AddAccount(account.AddAsset(asset))

        portfolio.WhatIf('Account', 'Asset', 20)
        portfolio.WhatIf('Account', 'Asset', 30)
        self.assertAlmostEqual(150, asset.AdjustedValue())
        self.assertAlmostEqual(-50, account.AvailableCash())
        self.assertAlmostEqual(100, portfolio.TotalValue())
        account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
        self.assertListEqual(
            [['Account', '-$50.00']],
            account_whatifs.StrList())
        self.assertListEqual(
            [['Account', 'Asset', '+$50.00']],
            asset_whatifs.StrList())

    def testReturnActualAllocationOneAsset(self):
        asset_class = AssetClass('All').Validate()
        allocation = {'All': 10.0}

        ret = asset_class.ReturnAllocation(allocation)
        self.assertEqual(1, len(ret))
        self.assertEqual('All', ret[0].name)
        self.assertAlmostEqual(10.0, ret[0].value)
        self.assertEqual([], ret[0].children)

    def testReturnActualAllocationAssetTree(self):
        asset_class = (
            AssetClass('All')
            .AddSubClass(0.6, AssetClass('Equity')
                         .AddSubClass(0.6, AssetClass('US'))
                         .AddSubClass(0.4, AssetClass('Intl')))
            .AddSubClass(0.4, AssetClass('Bonds'))).Validate()
        allocation = {'US': 10.0, 'Intl': 20.0, 'Bonds': 40.0}

        ret = asset_class.ReturnAllocation(allocation, levels=0)

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
                asset_class.ReturnAllocation(
                    allocation, levels=1)))
        self.assertEqual(
            5, len(
                asset_class.ReturnAllocation(
                    allocation, levels=2)))
        self.assertEqual(5, len(asset_class.ReturnAllocation(allocation)))
        self.assertEqual(
            5, len(
                asset_class.ReturnAllocation(
                    allocation, levels=5)))


if __name__ == '__main__':
    unittest.main()
