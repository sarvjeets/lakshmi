"""Tests for lakshmi.assets module."""
import datetime
import json
import pathlib
import unittest
from unittest.mock import MagicMock, patch

import ibonds

import lakshmi.assets as assets
import lakshmi.cache


class AssetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lakshmi.cache.set_cache_dir(None)  # Disable caching.
        cls.data_dir = (pathlib.Path(__file__).parent / 'data')

    def test_dict_manual_asset_with_what_if(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        manual_asset.what_if(100)
        manual_asset = assets.from_dict(assets.to_dict(manual_asset))
        self.assertEqual('Cash', manual_asset.name())
        self.assertAlmostEqual(100.5, manual_asset.value())
        self.assertAlmostEqual(200.5, manual_asset.adjusted_value())
        self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

    def test_asset_bad_what_if(self):
        a = assets.ManualAsset('Cash', 100, {'All': 1.0})
        a.what_if(-101)
        self.assertAlmostEqual(0, a.adjusted_value())

    def test_dict_manual_asset(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        manual_asset = assets.from_dict(assets.to_dict(manual_asset))
        self.assertEqual('Cash', manual_asset.name())
        self.assertAlmostEqual(100.5, manual_asset.adjusted_value())
        self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

    def test_manual_asset_to_table(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        expected = [['Name:', 'Cash'],
                    ['Asset Class Mapping:', 'Fixed Income  100%'],
                    ['Value:', '$100.50']]
        self.assertListEqual(expected, manual_asset.to_table().str_list())

        manual_asset.what_if(-100)
        expected = [['Name:', 'Cash'],
                    ['Asset Class Mapping:', 'Fixed Income  100%'],
                    ['Adjusted Value:', '$0.50'],
                    ['What if:', '-$100.00']]
        self.assertListEqual(expected, manual_asset.to_table().str_list())

    @patch('yfinance.Ticker')
    def test_bad_ticker(self, MockTicker):
        bad_ticker = MagicMock()
        bad_ticker.info = {}
        bad_ticker.fast_info = {}
        MockTicker.return_value = bad_ticker

        ticker_asset = assets.TickerAsset('bad', 10, {'All': 1.0})
        with self.assertRaisesRegex(assets.NotFoundError,
                                    'Cannot retrieve ticker'):
            ticker_asset.name()
        with self.assertRaisesRegex(assets.NotFoundError,
                                    'Cannot retrieve ticker'):
            ticker_asset.value()

        MockTicker.assert_called_once()

    @patch('yfinance.Ticker')
    def test_good_ticker(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'longName': 'Vanguard Cash Reserves Federal'}
        ticker.fast_info = {'lastPrice': 1.0}
        MockTicker.return_value = ticker

        vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
        self.assertAlmostEqual(100.0, vmmxx.value())
        self.assertEqual('Vanguard Cash Reserves Federal', vmmxx.name())
        self.assertEqual('VMMXX', vmmxx.short_name())

        MockTicker.assert_called_once()

    @patch('yfinance.Ticker')
    def test_missing_longname(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'shortName': 'Bitcoin USD',
                       'name': 'Bitcoin'}
        MockTicker.return_value = ticker

        btc = assets.TickerAsset('BTC-USD', 1.0, {'All': 1.0})
        self.assertEqual('Bitcoin USD', btc.name())

        MockTicker.assert_called_once()

    @patch('yfinance.Ticker')
    def test_missing_longname_shortname(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'name': 'Bitcoin'}
        ticker.fast_info = {'regularMarketPrice': 1.0}
        MockTicker.return_value = ticker

        btc = assets.TickerAsset('BTC-USD', 1.0, {'All': 1.0})
        self.assertEqual('Bitcoin', btc.name())

        MockTicker.assert_called_once()

    def test_tax_lots_ticker(self):
        vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
        lots = [assets.TaxLot('2012/12/12', 50, 1.0),
                assets.TaxLot('2013/12/12', 30, 0.9)]
        with self.assertRaisesRegex(AssertionError,
                                    'Lots provided should sum up to 100.0'):
            vmmxx.set_lots(lots)

        lots.append(assets.TaxLot('2014/12/31', 20, 0.9))
        vmmxx.set_lots(lots)
        self.assertListEqual(lots, vmmxx.get_lots())

    @patch('lakshmi.assets.TickerAsset.price')
    def test_list_lots(self, mock_price):
        mock_price.return_value = 15.0

        vti = assets.TickerAsset('VTI', 100.0, {'All': 1.0})
        lots = [assets.TaxLot('2011/01/01', 50, 10.0),
                assets.TaxLot('2012/01/01', 50, 20.0)]
        vti.set_lots(lots)

        self.assertListEqual(
            [['2011/01/01', '50.0', '$500.00', '+$250.00', '50.0%'],
             ['2012/01/01', '50.0', '$1,000.00', '-$250.00', '-25.0%']],
            vti.list_lots().str_list())

    @patch('lakshmi.assets._today')
    @patch('lakshmi.assets.TickerAsset.price')
    def test_list_lots_with_term(self, mock_price, mock_today):
        mock_price.return_value = 15.0
        mock_today.return_value = datetime.datetime.strptime(
            '2012/12/01', '%Y/%m/%d')

        vti = assets.TickerAsset('VTI', 150.0, {'All': 1.0})
        lots = [assets.TaxLot('2011/01/01', 50, 10.0),
                assets.TaxLot('2012/01/01', 50, 20.0),
                assets.TaxLot('2012/11/01', 50, 20.0)]
        vti.set_lots(lots)

        self.assertListEqual(
            [['2011/01/01', '50.0', '$500.00', '+$250.00', '50.0%', 'LT'],
             ['2012/01/01', '50.0', '$1,000.00', '-$250.00', '-25.0%', 'ST'],
             ['2012/11/01', '50.0', '$1,000.00', '-$250.00', '-25.0%', '30']],
            vti.list_lots(include_term=True).str_list())

    @patch('lakshmi.assets.TickerAsset.name')
    @patch('lakshmi.assets.TickerAsset.price')
    def test_ticker_asset_to_table(self, mock_price, mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Google Inc'

        goog = assets.TickerAsset('GOOG', 100.0, {'All': 1.0})
        expected = [['Ticker:', 'GOOG'],
                    ['Name:', 'Google Inc'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Price:', '$10.00']]
        self.assertListEqual(expected, goog.to_table().str_list())

    @patch('yfinance.Ticker')
    def test_dict_ticker(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'longName': 'Vanguard Cash Reserves Federal'}
        ticker.fast_info = {'lastPrice': 1.0}
        MockTicker.return_value = ticker

        vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
        lots = [assets.TaxLot('2012/12/12', 50, 1.0),
                assets.TaxLot('2013/12/12', 50, 0.9)]
        vmmxx.set_lots(lots)
        vmmxx.what_if(-10)
        vmmxx = assets.from_dict(assets.to_dict(vmmxx))
        self.assertEqual('VMMXX', vmmxx.short_name())
        self.assertEqual(100.0, vmmxx.shares())
        self.assertEqual({'All': 1.0}, vmmxx.class2ratio)
        self.assertAlmostEqual(90.0, vmmxx.adjusted_value())
        self.assertEqual(2, len(vmmxx.get_lots()))

    @patch('requests.get')
    def test_vanguard_funds_name(self, mock_get):
        mock_res = MagicMock()

        with open(self.data_dir / 'profile.json') as data_file:
            mock_res.json.return_value = json.load(data_file)

        mock_get.return_value = mock_res

        fund = assets.VanguardFund(7555, 10, {'All': 1.0})
        self.assertEqual(
            'Vanguard Institutional Total Bond Market Index Trust',
            fund.name())
        self.assertEqual('7555', fund.short_name())
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
        self.assertEqual(1166.6, fund.value())
        mock_get.assert_called_once_with(
            'https://api.vanguard.com/rs/ire/01/pe/fund/7555/price.json',
            headers={'Referer': 'https://vanguard.com/'})
        fund.set_lots([assets.TaxLot('2012/12/30', 10, 1.0)])

    @patch('lakshmi.assets.VanguardFund.value')
    def test_dict_vanguard_fund(self, mock_value):
        mock_value.return_value = 100.0
        fund = assets.VanguardFund(1234, 20, {'Bonds': 1.0})
        fund.set_lots([assets.TaxLot('2021/05/15', 20, 5.0)])
        fund.what_if(100)
        fund = assets.from_dict(assets.to_dict(fund))
        self.assertEqual('1234', fund.short_name())
        self.assertEqual(20, fund.shares())
        self.assertEqual({'Bonds': 1.0}, fund.class2ratio)
        self.assertEqual(1, len(fund.get_lots()))
        self.assertEqual(100, fund._delta)

    @patch('lakshmi.assets.VanguardFund.name')
    @patch('lakshmi.assets.VanguardFund.price')
    def test_vangurd_fund_asset_to_table(self, mock_price, mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Vanguardy Fund'

        fund = assets.VanguardFund(123, 100.0, {'All': 1.0})
        expected = [['Fund id:', '123'],
                    ['Name:', 'Vanguardy Fund'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Price:', '$10.00']]
        self.assertListEqual(expected, fund.to_table().str_list())

    @patch('lakshmi.assets._today_date')
    @patch('lakshmi.assets.IBonds._InterestRates.get')
    def test_i_bonds(self, mock_get, mock_today):
        INTEREST_RATE_DATA = """
        2020-11-01:
        - 0.00
        - 0.84
        2021-05-01:
        - 0.00
        - 1.77
        """
        mock_get.return_value = ibonds.InterestRates(INTEREST_RATE_DATA)
        ibond_asset = assets.IBonds({'All': 1.0})
        ibond_asset.add_bond('11/2020', 10000)

        self.assertEqual('I Bonds', ibond_asset.name())
        self.assertEqual('I Bonds', ibond_asset.short_name())

        mock_today.return_value = datetime.date(2020, 11, 2)
        self.assertListEqual(
            [['11/2020', '$10,000.00', '0.00%', '1.68%', '$10,000.00']],
            ibond_asset.list_bonds().str_list())

        # Test the case where the interest rate data is not up to date.
        mock_today.return_value = datetime.date(2021, 11, 1)
        self.assertListEqual(
            [['11/2020', '$10,000.00', '0.00%', '', '$10,172.00']],
            ibond_asset.list_bonds().str_list())

    @patch('lakshmi.assets.IBonds.value')
    def test_dict_i_bonds(self, mock_value):
        mock_value.return_value = 11000
        ibonds = assets.IBonds({'B': 1.0})
        ibonds.add_bond('02/2020', 10000)
        ibonds.what_if(-100.0)

        ibonds = assets.from_dict(assets.to_dict(ibonds))
        self.assertEqual('I Bonds', ibonds.name())
        self.assertEqual({'B': 1.0}, ibonds.class2ratio)
        self.assertAlmostEqual(-100.0, ibonds._delta)
        self.assertEqual(1, len(ibonds.bonds()))

    @patch('datetime.datetime')
    @patch('requests.post')
    def test_ee_bonds(self, mock_post, mock_date):
        mock_res = MagicMock()
        with open(self.data_dir / 'SBCPrice-EE.html') as html_file:
            mock_res.text = html_file.read()
        mock_post.return_value = mock_res
        mock_date.now.strftime.return_value = '04/2021'
        # Bypass issue date validation.
        mock_strptime = MagicMock()
        mock_strptime.strftime.return_value = '03/2020'
        mock_date.strptime.return_value = mock_strptime

        eebonds = assets.EEBonds({'All': 1.0})
        eebonds.add_bond('3/2020', 10000)

        mock_post.asset_called_once_with(
            'http://www.treasurydirect.gov/BC/SBCPrice',
            data={
                'RedemptionDate': '04/2021',
                'Series': 'EE',
                'Denomination': '500',
                'IssueDate': '03/2020',
                'btnAdd.x': 'CALCULATE'})

        self.assertEqual('EE Bonds', eebonds.name())
        self.assertEqual('EE Bonds', eebonds.short_name())
        self.assertAlmostEqual(10008.0, eebonds.value())
        self.assertListEqual(
            [['03/2020', '$10,000.00', '0.10%', '$10,008.00']],
            eebonds.list_bonds().str_list())

    @patch('lakshmi.assets.EEBonds.value')
    def test_dict_ee_bonds(self, mock_value):
        mock_value.return_value = 10010
        eebonds = assets.EEBonds({'B': 1.0})
        eebonds.add_bond('02/2020', 10000)
        eebonds.what_if(-100.0)
        eebonds = assets.from_dict(assets.to_dict(eebonds))
        self.assertEqual('EE Bonds', eebonds.name())
        self.assertEqual({'B': 1.0}, eebonds.class2ratio)
        self.assertAlmostEqual(-100.0, eebonds._delta)
        self.assertEqual(1, len(eebonds.bonds()))


if __name__ == '__main__':
    unittest.main()
