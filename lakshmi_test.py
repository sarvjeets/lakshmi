#!/usr/bin/python3

import assets
import lakshmi

import unittest

class LakshmiTest(unittest.TestCase):
  def test_EmptyInterface(self):
    interface = lakshmi.Interface(lakshmi.AssetClass('E'))
    self.assertEqual('\nTotal: $0.00\n', interface.ListAssets())

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

  def test_DummyAssetWithBadAsset(self):
    interface = lakshmi.Interface(lakshmi.AssetClass('Equity'))

    # Create a dummy asset.
    account = lakshmi.Account('Roth IRA', 'Post-tax').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0, {'Bad Equity': 1.0}))
    with self.assertRaisesRegex(lakshmi.ValidationError,
                                'Unknown or non-leaf asset class: Bad Equity'):
      interface.AddAccount(account)

  def test_OneDummyAsset(self):
    interface = lakshmi.Interface(lakshmi.AssetClass('Equity'))

    # Create a dummy asset.
    account = lakshmi.Account('401(k)', 'Pre-tax').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0, {'Equity': 1.0}))

    interface.AddAccount(account)
    self.assertEqual(1, len(interface.accounts))

    self.assertEqual(
      '401(k), Test Asset, $100.00\n\nTotal: $100.00\n',
      interface.ListAssets())

    self.assertEqual(
      'Pre-tax, $100.00, 100%\n', interface.AssetLocation())

    self.assertEqual(
      'Equity: $100.00\n', interface.AssetAllocation())

  def test_OneDummyAssetTwoClass(self):
    AssetClass = lakshmi.AssetClass
    asset_class = (
      AssetClass('All')
        .AddSubClass(0.5, AssetClass('Equity'))
        .AddSubClass(0.5, AssetClass('Fixed Income')))

    interface = lakshmi.Interface(asset_class)

    account = lakshmi.Account('Vanguard', 'Taxable').AddAsset(
      assets.SimpleAsset('Test Asset', 100.0,
                         {'Equity': 0.6, 'Fixed Income': 0.4}))

    interface.AddAccount(account)
    self.assertEqual(
      'Vanguard, Test Asset, $100.00\n\nTotal: $100.00\n',
      interface.ListAssets())

    self.assertEqual(
      'Taxable, $100.00, 100%\n', interface.AssetLocation())

    self.assertEqual(
      'All: $100.00\nEquity: 60% (50%), -$10.00\nFixed Income: 40% (50%), +$10.00\n\n'
      'Equity: $60.00\n\nFixed Income: $40.00\n',
      interface.AssetAllocation())

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
