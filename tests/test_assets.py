"""Tests for lakshmi.assets module."""
import json
import lakshmi.assets as assets
import lakshmi.cache
import pathlib
import unittest
from unittest.mock import MagicMock, patch


class AssetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lakshmi.cache.set_cache_dir(None)  # Disable caching.
        cls.data_dir = (pathlib.Path(__file__).parent / 'data')

    def test_dict_manual_asset_with_what_if(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        manual_asset.WhatIf(100)
        manual_asset = assets.FromDict(assets.ToDict(manual_asset))
        self.assertEqual('Cash', manual_asset.Name())
        self.assertAlmostEqual(100.5, manual_asset.Value())
        self.assertAlmostEqual(200.5, manual_asset.AdjustedValue())
        self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

    def test_asset_bad_what_if(self):
        a = assets.ManualAsset('Cash', 100, {'All': 1.0})
        self.assertAlmostEqual(-100, a.WhatIf(-101))
        self.assertAlmostEqual(0, a.AdjustedValue())

    def test_dict_manual_asset(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        manual_asset = assets.FromDict(assets.ToDict(manual_asset))
        self.assertEqual('Cash', manual_asset.Name())
        self.assertAlmostEqual(100.5, manual_asset.AdjustedValue())
        self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

    def test_manual_asset_to_table(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        expected = [['Name:', 'Cash'],
                    ['Asset Class Mapping:', 'Fixed Income  100%'],
                    ['Value:', '$100.50']]
        self.assertListEqual(expected, manual_asset.ToTable().StrList())

        manual_asset.WhatIf(-100)
        expected = [['Name:', 'Cash'],
                    ['Asset Class Mapping:', 'Fixed Income  100%'],
                    ['Adjusted Value:', '$0.50'],
                    ['What if:', '-$100.00']]
        self.assertListEqual(expected, manual_asset.ToTable().StrList())

    @patch('yfinance.Ticker')
    def test_bad_ticker(self, MockTicker):
        bad_ticker = MagicMock()
        bad_ticker.info = {}
        MockTicker.return_value = bad_ticker

        ticker_asset = assets.TickerAsset('bad', 10, {'All': 1.0})

        with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
            ticker_asset.Name()
        with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
            ticker_asset.Value()

        MockTicker.assert_called_once()

    @patch('yfinance.Ticker')
    def test_good_ticker(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                       'regularMarketPrice': 1.0}
        MockTicker.return_value = ticker

        vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
        self.assertAlmostEqual(100.0, vmmxx.Value())
        self.assertEqual('Vanguard Cash Reserves Federal', vmmxx.Name())
        self.assertEqual('VMMXX', vmmxx.ShortName())

        MockTicker.assert_called_once()

    def test_tax_lots_ticker(self):
        vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
        lots = [assets.TaxLot('2012/12/12', 50, 1.0),
                assets.TaxLot('2013/12/12', 30, 0.9)]
        with self.assertRaisesRegex(AssertionError,
                                    'Lots provided should sum up to 100.0'):
            vmmxx.SetLots(lots)

        lots.append(assets.TaxLot('2014/12/31', 20, 0.9))
        vmmxx.SetLots(lots)
        self.assertListEqual(lots, vmmxx.tax_lots)

    @patch('lakshmi.assets.TickerAsset.Price')
    def test_list_lots(self, mock_price):
        mock_price.return_value = 15.0

        vti = assets.TickerAsset('VTI', 100.0, {'All': 1.0})
        lots = [assets.TaxLot('2011/01/01', 50, 10.0),
                assets.TaxLot('2012/01/01', 50, 20.0)]
        vti.SetLots(lots)

        self.assertListEqual(
                [['2011/01/01', '50.0', '$500.00', '+$250.00', '50%'],
                 ['2012/01/01', '50.0', '$1,000.00', '-$250.00', '-25%']],
                vti.ListLots().StrList())

    @patch('lakshmi.assets.TickerAsset.Name')
    @patch('lakshmi.assets.TickerAsset.Price')
    def test_ticker_asset_to_table(self, mock_price, mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Google Inc'

        goog = assets.TickerAsset('GOOG', 100.0, {'All': 1.0})
        expected = [['Ticker:', 'GOOG'],
                    ['Name:', 'Google Inc'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Price:', '$10.00']]
        self.assertListEqual(expected, goog.ToTable().StrList())

    @patch('yfinance.Ticker')
    def test_dict_ticker(self, MockTicker):
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
    def test_vanguard_funds_name(self, mock_get):
        mock_res = MagicMock()

        with open(self.data_dir / 'profile.json') as data_file:
            mock_res.json.return_value = json.load(data_file)

        mock_get.return_value = mock_res

        fund = assets.VanguardFund(7555, 10, {'All': 1.0})
        self.assertEqual(
            'Vanguard Institutional Total Bond Market Index Trust',
            fund.Name())
        self.assertEqual('7555', fund.ShortName())
        mock_get.assert_called_once_with(
            'https://api.vanguard.com/rs/ire/01/pe/fund/7555/profile.json',
            headers={'Referer': 'https://vanguard.com/'})

    @patch('requests.get')
    def test_vanguard_funds_value(self, mock_get):
        mock_res = MagicMock()

        with open(self.data_dir / 'price.json') as data_file:
            mock_res.json.return_value = json.load(data_file)
        mock_get.return_value = mock_res

        fund = assets.VanguardFund(7555, 10, {'All': 1.0})
        self.assertEqual(1166.6, fund.Value())
        mock_get.assert_called_once_with(
            'https://api.vanguard.com/rs/ire/01/pe/fund/7555/price.json',
            headers={'Referer': 'https://vanguard.com/'})
        fund.SetLots([assets.TaxLot('2012/12/30', 10, 1.0)])

    @patch('lakshmi.assets.VanguardFund.Value')
    def test_dict_vanguard_fund(self, mock_value):
        mock_value.return_value = 100.0
        fund = assets.VanguardFund(1234, 20, {'Bonds': 1.0})
        fund.SetLots([assets.TaxLot('2021/05/15', 20, 5.0)])
        fund.WhatIf(100)
        fund = assets.FromDict(assets.ToDict(fund))
        self.assertEqual(1234, fund.fund_id)
        self.assertEqual(20, fund.shares)
        self.assertEqual({'Bonds': 1.0}, fund.class2ratio)
        self.assertEqual(1, len(fund.tax_lots))
        self.assertEqual(100, fund._delta)

    @patch('lakshmi.assets.VanguardFund.Name')
    @patch('lakshmi.assets.VanguardFund.Price')
    def test_vangurd_fund_asset_to_table(self, mock_price, mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Vanguardy Fund'

        fund = assets.VanguardFund(123, 100.0, {'All': 1.0})
        expected = [['Fund id:', '123'],
                    ['Name:', 'Vanguardy Fund'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Price:', '$10.00']]
        self.assertListEqual(expected, fund.ToTable().StrList())

    @patch('datetime.datetime')
    @patch('requests.post')
    def test_i_bonds(self, mock_post, mock_date):
        mock_res = MagicMock()
        with open(self.data_dir / 'SBCPrice-I.html') as html_file:
            mock_res.text = html_file.read()
        mock_post.return_value = mock_res
        mock_date.now.strftime.return_value = '04/2021'

        ibonds = assets.IBonds({'All': 1.0})
        ibonds.AddBond('03/2020', 10000)

        mock_post.asset_called_once_with(
            'http://www.treasurydirect.gov/BC/SBCPrice',
            data={
                'RedemptionDate': '04/2021',
                'Series': 'I',
                'Denomination': '1000',
                'IssueDate': '03/2020',
                'btnAdd.x': 'CALCULATE'})

        self.assertEqual('I Bonds', ibonds.Name())
        self.assertEqual('I Bonds', ibonds.ShortName())
        self.assertAlmostEqual(10156.0, ibonds.Value())
        self.assertListEqual(
                [['03/2020', '$10,000.00', '1.88%', '$10,156.00']],
                ibonds.ListBonds().StrList())

    @patch('lakshmi.assets.IBonds.Value')
    def test_dict_i_bonds(self, mock_value):
        mock_value.return_value = 11000
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
    def test_ee_bonds(self, mock_post, mock_date):
        mock_res = MagicMock()
        with open(self.data_dir / 'SBCPrice-EE.html') as html_file:
            mock_res.text = html_file.read()
        mock_post.return_value = mock_res
        mock_date.now.strftime.return_value = '04/2021'

        eebonds = assets.EEBonds({'All': 1.0})
        eebonds.AddBond('03/2020', 10000)

        mock_post.asset_called_once_with(
            'http://www.treasurydirect.gov/BC/SBCPrice',
            data={
                'RedemptionDate': '04/2021',
                'Series': 'EE',
                'Denomination': '500',
                'IssueDate': '03/2020',
                'btnAdd.x': 'CALCULATE'})

        self.assertEqual('EE Bonds', eebonds.Name())
        self.assertEqual('EE Bonds', eebonds.ShortName())
        self.assertAlmostEqual(10008.0, eebonds.Value())
        self.assertListEqual(
                [['03/2020', '$10,000.00', '0.10%', '$10,008.00']],
                eebonds.ListBonds().StrList())

    @patch('lakshmi.assets.EEBonds.Value')
    def test_dict_ee_bonds(self, mock_value):
        mock_value.return_value = 10010
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
