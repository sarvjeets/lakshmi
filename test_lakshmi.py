#!/usr/bin/python3

import assets
import lakshmi

import unittest

class LakshmiTest(unittest.TestCase):
  def test_EmptyPortfolio(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('E'))
    self.assertListEqual([], portfolio.Assets())
    self.assertAlmostEqual(0, portfolio.TotalValue())
    self.assertListEqual([], portfolio.Assets())
    self.assertEqual('', portfolio.AssetsAsStr())
    self.assertListEqual([], portfolio.AssetLocation())
    self.assertEqual('', portfolio.AssetLocationAsStr())
    self.assertListEqual([], portfolio.AssetAllocationTree())
    self.assertEqual('', portfolio.AssetAllocationTreeAsStr())

  def test_OneAssetClass(self):
    asset_class = lakshmi.AssetClass('Equity').Validate()

  def test_ManyAssetClassDuplicate(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.8,
                     AssetClass('Equity')
                       .AddSubClass(0.6, AssetClass('US'))
                       .AddSubClass(0.4, AssetClass('International')))
        .AddSubClass(0.2, AssetClass('US')))
    with self.assertRaisesRegex(lakshmi.ValidationError, 'Found duplicate'):
      asset_class.Validate()

  def test_ManyAssetClassBadRatioSum(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.8,
                     AssetClass('Equity')
                       .AddSubClass(0.6, AssetClass('US'))
                       .AddSubClass(0.5, AssetClass('International')))
        .AddSubClass(0.2, AssetClass('Bonds')))

    with self.assertRaisesRegex(lakshmi.ValidationError, 'Sum of sub-classes'):
      asset_class.Validate()

  def test_ManyAssetClassBadRatioNeg(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(-0.8,
                     AssetClass('Equity')
                       .AddSubClass(0.6, AssetClass('US'))
                       .AddSubClass(0.4, AssetClass('International')))
        .AddSubClass(0.2, AssetClass('Bonds')))

    with self.assertRaisesRegex(lakshmi.ValidationError, 'Bad ratio'):
      asset_class.Validate()

  def test_ManyAssetClassBadRatioHigh(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(1.5,
                     AssetClass('Equity')
                       .AddSubClass(0.6, AssetClass('US'))
                       .AddSubClass(0.4, AssetClass('International')))
        .AddSubClass(0.2, AssetClass('Bonds')))

    with self.assertRaisesRegex(lakshmi.ValidationError, 'Bad ratio'):
      asset_class.Validate()

  def test_ManyAssetClass(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.8,
                     AssetClass('Equity')
                       .AddSubClass(0.6, AssetClass('US'))
                       .AddSubClass(0.4, AssetClass('International')))
        .AddSubClass(0.2, AssetClass('Bonds'))).Validate()

    self.assertEqual({'US', 'International', 'Bonds'}, asset_class.Leaves())

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

  def test_AssetClassCopy(self):
    AssetClass = lakshmi.AssetClass
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

  def test_ValueMapped(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.6, AssetClass('Equity')
                     .AddSubClass(0.6, AssetClass('US'))
                     .AddSubClass(0.4, AssetClass('Intl')))
        .AddSubClass(0.4, AssetClass('Bonds')))

    with self.assertRaisesRegex(lakshmi.ValidationError, 'Need to validate'):
      asset_class.ValueMapped({})

    asset_class.Validate()
    money_allocation = {'US': 10.0, 'Intl': 20.0, 'Bonds': 40.0, 'Unused': 50.0}

    self.assertAlmostEqual(70.0, asset_class.ValueMapped(money_allocation))
    self.assertAlmostEqual(30.0, asset_class.children[0][0].ValueMapped(money_allocation))
    self.assertAlmostEqual(40.0, asset_class.children[1][0].ValueMapped(money_allocation))

  def test_BadAsset(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('Equity'))

    account = lakshmi.Account('Roth IRA', 'Post-tax').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0, {'Bad Equity': 1.0}))
    with self.assertRaisesRegex(lakshmi.ValidationError,
                                'Unknown or non-leaf asset class: Bad Equity'):
      portfolio.AddAccount(account)

  def test_DuplicateAccount(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('All'))
    account = lakshmi.Account('Roth IRA', 'Post-tax').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0, {'All': 1.0}))
    portfolio.AddAccount(account)
    with self.assertRaisesRegex(lakshmi.ValidationError,
                                'Attempting to add'):
      portfolio.AddAccount(account)

  def test_GetAssetFromAccount(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('All'))
    account = lakshmi.Account('Roth IRA', 'Post-tax').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0, {'All': 1.0}))
    portfolio.AddAccount(account)
    asset = account.GetAsset('Test Asset')
    self.assertEqual('Test Asset', asset.Name())
    self.assertAlmostEqual(100.0, asset.Value())

  def test_OneAsset(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('Equity'))

    # Create a dummy asset.
    account = lakshmi.Account('401(k)', 'Pre-tax').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0, {'Equity': 1.0}))

    portfolio.AddAccount(account)
    self.assertEqual(1, len(portfolio.Accounts()))

    self.assertListEqual([['401(k)', 'Test Asset', '$100.00']],
                         portfolio.Assets())
    self.assertAlmostEqual(100.0, portfolio.TotalValue())

    self.assertListEqual([['Pre-tax', '$100.00', '100%']],
                         portfolio.AssetLocation())

    self.assertListEqual([], portfolio.AssetAllocationTree())

  def test_AssetWhatIf(self):
    asset = assets.SimpleAsset('Test Asset', 100.0, {'Equity': 1.0})
    self.assertAlmostEqual(100, asset.AdjustedValue())
    asset.WhatIf(-10.0)
    self.assertAlmostEqual(100, asset.Value())
    self.assertAlmostEqual(90, asset.AdjustedValue())
    asset.WhatIf(10)
    self.assertAlmostEqual(100, asset.AdjustedValue())

  def test_OneAssetTwoClass(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.5, AssetClass('Equity'))
        .AddSubClass(0.5, AssetClass('Fixed Income')))

    portfolio = lakshmi.Portfolio(asset_class)

    account = lakshmi.Account('Vanguard', 'Taxable').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0,
                         {'Equity': 0.6, 'Fixed Income': 0.4}))

    portfolio.AddAccount(account)
    self.assertListEqual([['Vanguard', 'Test Asset', '$100.00']],
                         portfolio.Assets())
    self.assertAlmostEqual(100.0, portfolio.TotalValue())

    self.assertListEqual([['Taxable', '$100.00', '100%']],
                         portfolio.AssetLocation())

    self.assertListEqual(
      [['-\nAll:'],
       ['Equity', '60%', '50%', '$60.00'],
       ['Fixed Income', '40%', '50%', '$40.00']],
      portfolio.AssetAllocationTree())

  def test_FlatAssetAllocation(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.8,
                     AssetClass('Equity')
                       .AddSubClass(0.6, AssetClass('US'))
                       .AddSubClass(0.4, AssetClass('Intl')))
        .AddSubClass(0.2, AssetClass('Bonds'))).Validate()
    portfolio = lakshmi.Portfolio(asset_class)
    Asset = assets.SimpleAsset
    portfolio.AddAccount(
      lakshmi.Account('Account', 'Taxable')
      .AddAsset(Asset('US Asset', 60.0, {'US': 1.0}))
      .AddAsset(Asset('Intl Asset', 30.0, {'Intl': 1.0}))
      .AddAsset(Asset('Bond Asset', 10.0, {'Bonds': 1.0})))

    with self.assertRaisesRegex(lakshmi.ValidationError,
                                'AssetAllocation called with'):
      portfolio.AssetAllocation(['Equity', 'Intl'])

    self.assertListEqual(
      [['US', '60%', '48%', '$60.00', '-$12.00'],
       ['Intl', '30%', '32%', '$30.00', '+$2.00'],
       ['Bonds', '10%', '20%', '$10.00', '+$10.00']],
      portfolio.AssetAllocation(['US', 'Intl', 'Bonds']))

    self.assertListEqual(
      [['Equity', '90%', '80%', '$90.00', '-$10.00'],
       ['Bonds', '10%', '20%', '$10.00', '+$10.00']],
      portfolio.AssetAllocation(['Equity', 'Bonds']))

  def test_PortfolioStringMethods(self):
    # This test doesn't do much except that the string methods
    # "compile". In any case, they don't have much logic in them
    # by design.
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.5, AssetClass('Equity'))
        .AddSubClass(0.5, AssetClass('Fixed Income')))
    portfolio = lakshmi.Portfolio(asset_class)
    account = lakshmi.Account('Vanguard', 'Taxable').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0,
                         {'Equity': 0.6, 'Fixed Income': 0.4}))
    portfolio.AddAccount(account)

    self.assertIsInstance(portfolio.AssetsAsStr(), str)
    self.assertIsInstance(portfolio.AssetLocationAsStr(), str)
    self.assertIsInstance(portfolio.AssetAllocationTreeAsStr(), str)
    self.assertIsInstance(portfolio.AssetAllocationAsStr(
      ['Equity', 'Fixed Income']), str)

  def test_MultipleAccountsAndAssets(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('All'))
    asset_class_map = {'All': 1.0}

    (portfolio
     .AddAccount(
       lakshmi.Account('Account 1', 'Taxable')
       .AddAsset(assets.SimpleAsset('Asset 1', 100.0, asset_class_map))
       .AddAsset(assets.SimpleAsset('Asset 2', 200.0, asset_class_map)))
     .AddAccount(
       lakshmi.Account('Account 2', 'Roth IRA')
       .AddAsset(assets.SimpleAsset('Asset 1', 300.0, asset_class_map))
       .AddAsset(assets.SimpleAsset('Asset 2', 400.0, asset_class_map))))

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
      portfolio.Assets())

  def test_WhatIfs(self):
    AssetClass = lakshmi.AssetClass
    portfolio = lakshmi.Portfolio(AssetClass('All')
                                  .AddSubClass(0.6, AssetClass('Equity'))
                                  .AddSubClass(0.4, AssetClass('Bonds')))
    asset1 = assets.SimpleAsset('Asset 1', 100.0, {'Equity': 1.0})
    asset2 = assets.SimpleAsset('Asset 2', 100.0, {'Bonds': 1.0})
    account1 = lakshmi.Account('Account 1', 'Taxable')
    account1.AddAsset(asset1).AddAsset(asset2)
    account2 = lakshmi.Account('Account 2', 'Pre-tax')
    portfolio.AddAccount(account1).AddAccount(account2)

    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual([], account_whatifs)
    self.assertListEqual([], asset_whatifs)

    portfolio.WhatIf('Account 1', 'Asset 2', -20)
    self.assertAlmostEqual(80, asset2.AdjustedValue())
    self.assertAlmostEqual(20, account1.AvailableCash())
    self.assertAlmostEqual(200, portfolio.TotalValue())
    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual([['Account 1', '+$20.00']], account_whatifs)
    self.assertListEqual(
      [['Account 1', 'Asset 2', '-$20.00']],
      asset_whatifs)

    portfolio.WhatIf('Account 1', 'Asset 1', 20)
    self.assertAlmostEqual(120, asset1.AdjustedValue())
    self.assertAlmostEqual(0, account1.AvailableCash())
    self.assertAlmostEqual(200, portfolio.TotalValue())
    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual([], account_whatifs)
    self.assertListEqual(
      [['Account 1', 'Asset 1', '+$20.00'],
       ['Account 1', 'Asset 2', '-$20.00']],
      asset_whatifs)

    self.assertListEqual(
      [['Account 1', 'Asset 1', '$120.00'],
       ['Account 1', 'Asset 2', '$80.00']],
      portfolio.Assets())

    self.assertListEqual(
      [['-\nAll:'],
       ['Equity', '60%', '60%', '$120.00'],
       ['Bonds', '40%', '40%', '$80.00']],
      portfolio.AssetAllocationTree())

    portfolio.WhatIfAddCash('Account 1', 30)
    self.assertAlmostEqual(30, account1.AvailableCash())
    self.assertAlmostEqual(230, portfolio.TotalValue())
    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual([['Account 1', '+$30.00']], account_whatifs)
    self.assertListEqual(
      [['Account 1', 'Asset 1', '+$20.00'],
       ['Account 1', 'Asset 2', '-$20.00']],
      asset_whatifs)

    portfolio.WhatIfAddCash('Account 2', 460)
    self.assertAlmostEqual(460, account2.AvailableCash())
    self.assertAlmostEqual(690, portfolio.TotalValue())
    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual(
      [['Account 1', '+$30.00'],
       ['Account 2', '+$460.00']],
      account_whatifs)
    self.assertListEqual(
      [['Account 1', 'Asset 1', '+$20.00'],
       ['Account 1', 'Asset 2', '-$20.00']],
      asset_whatifs)

    self.assertListEqual(
      [['Taxable', '$230.00', '33%'],
       ['Pre-tax', '$460.00', '67%']],
      portfolio.AssetLocation())

    portfolio.ResetWhatIfs()
    self.assertAlmostEqual(100, asset1.AdjustedValue())
    self.assertAlmostEqual(100, asset2.AdjustedValue())
    self.assertAlmostEqual(0, account1.AvailableCash())
    self.assertAlmostEqual(0, account2.AvailableCash())
    self.assertAlmostEqual(200, portfolio.TotalValue())
    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual([], account_whatifs)
    self.assertListEqual([], asset_whatifs)

  def test_WhatIfsDoubleAdd(self):
    portfolio = lakshmi.Portfolio(lakshmi.AssetClass('All'))

    asset = assets.SimpleAsset('Asset', 100.0, {'All': 1.0})
    account = lakshmi.Account('Account', 'Taxable')
    portfolio.AddAccount(account.AddAsset(asset))

    portfolio.WhatIf('Account', 'Asset', 20)
    portfolio.WhatIf('Account', 'Asset', 30)
    self.assertAlmostEqual(150, asset.AdjustedValue())
    self.assertAlmostEqual(-50, account.AvailableCash())
    self.assertAlmostEqual(100, portfolio.TotalValue())
    account_whatifs, asset_whatifs = portfolio.GetWhatIfs()
    self.assertListEqual([['Account', '-$50.00']], account_whatifs)
    self.assertListEqual([['Account', 'Asset', '+$50.00']], asset_whatifs)

  def test_ReturnActualAllocationOneAsset(self):
    AssetClass = lakshmi.AssetClass
    asset_class = AssetClass('All').Validate()

    allocation = {'All': 10.0}

    ret = asset_class.ReturnAllocation(allocation)
    self.assertEqual(1, len(ret))
    self.assertEqual('All', ret[0].name)
    self.assertAlmostEqual(10.0, ret[0].value)
    self.assertEqual([], ret[0].children)

  def test_ReturnActualAllocationAssetTree(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.6, AssetClass('Equity')
                     .AddSubClass(0.6, AssetClass('US'))
                     .AddSubClass(0.4, AssetClass('Intl')))
        .AddSubClass(0.4, AssetClass('Bonds'))).Validate()
    allocation = {'US': 10.0, 'Intl': 20.0, 'Bonds': 40.0}

    ret = asset_class.ReturnAllocation(allocation, levels = 0)

    self.assertEqual(1, len(ret))
    self.assertEqual('All', ret[0].name)
    self.assertAlmostEqual(70.0, ret[0].value)

    self.assertEqual(2, len(ret[0].children))
    self.assertEqual('Equity', ret[0].children[0].name)
    self.assertAlmostEqual(0.429, ret[0].children[0].actual_allocation, places = 3)
    self.assertAlmostEqual(0.6, ret[0].children[0].desired_allocation)
    self.assertAlmostEqual(12.0, ret[0].children[0].value_difference)
    self.assertEqual('Bonds', ret[0].children[1].name)
    self.assertAlmostEqual(0.571, ret[0].children[1].actual_allocation, places = 3)
    self.assertAlmostEqual(0.4, ret[0].children[1].desired_allocation)
    self.assertAlmostEqual(-12.0, ret[0].children[1].value_difference)

    self.assertEqual(3, len(asset_class.ReturnAllocation(allocation, levels = 1)))
    self.assertEqual(5, len(asset_class.ReturnAllocation(allocation, levels = 2)))
    self.assertEqual(5, len(asset_class.ReturnAllocation(allocation)))
    self.assertEqual(5, len(asset_class.ReturnAllocation(allocation, levels = 5)))


if __name__ == '__main__':
  unittest.main()