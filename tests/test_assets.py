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

    def test_dict_manual_asset_without_expense(self):
        manual_asset = assets.ManualAsset('Cash', 100.5, {'Fixed Income': 1.0})
        manual_asset = assets.from_dict(assets.to_dict(manual_asset))
        self.assertEqual('Cash', manual_asset.name())
        self.assertAlmostEqual(100.5, manual_asset.adjusted_value())
        self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)

    def test_dict_manual_asset_with_expense(self):
        manual_asset = assets.ManualAsset('Cash', 100.5,
                                          {'Fixed Income': 1.0},
                                          0.01)
        manual_asset = assets.from_dict(assets.to_dict(manual_asset))
        self.assertEqual('Cash', manual_asset.name())
        self.assertAlmostEqual(100.5, manual_asset.adjusted_value())
        self.assertEqual({'Fixed Income': 1.0}, manual_asset.class2ratio)
        self.assertEqual(0.01, manual_asset.expense_ratio())

    def test_manual_asset_to_table_without_expense(self):
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

    def test_manual_asset_to_table_with_expense(self):
        manual_asset = assets.ManualAsset(
            'Cash', 100.5, {'Fixed Income': 1.0}, 0.01)
        expected = [['Name:', 'Cash'],
                    ['Asset Class Mapping:', 'Fixed Income  100%'],
                    ['Value:', '$100.50'],
                    ['Expense ratio:', '0.01%']]
        self.assertListEqual(expected, manual_asset.to_table().str_list())

        manual_asset.what_if(-100)
        expected = [['Name:', 'Cash'],
                    ['Asset Class Mapping:', 'Fixed Income  100%'],
                    ['Adjusted Value:', '$0.50'],
                    ['What if:', '-$100.00'],
                    ['Expense ratio:', '0.01%']]
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
    @patch('lakshmi.assets.TickerAsset._fetch_expense_ratio')
    def test_ticker_asset_to_table(self, mock_ratio, mock_price, mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Google Inc'
        mock_ratio.return_value = 0.01

        goog = assets.TickerAsset('GOOG', 100.0, {'All': 1.0})
        expected = [['Ticker:', 'GOOG'],
                    ['Name:', 'Google Inc'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Expense ratio:', '0.01%'],
                    ['Price:', '$10.00']]
        self.assertListEqual(expected, goog.to_table().str_list())

    @patch('lakshmi.assets.TickerAsset.name')
    @patch('lakshmi.assets.TickerAsset.price')
    @patch('lakshmi.assets.TickerAsset._fetch_expense_ratio')
    def test_ticker_asset_to_table_with_expense(
            self, mock_ratio, mock_price, mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Google Inc'
        mock_ratio.return_value = 0.9

        # The expense ratio specified here should override 0.9 specified above.
        goog = assets.TickerAsset('GOOG', 100.0, {'All': 1.0}, 0.01)
        expected = [['Ticker:', 'GOOG'],
                    ['Name:', 'Google Inc'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Expense ratio:', '0.01%'],
                    ['Price:', '$10.00']]
        self.assertListEqual(expected, goog.to_table().str_list())

    @patch('yfinance.Ticker')
    def test_dict_ticker_without_expense(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                       'netExpenseRatio': 0.01}
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
        self.assertAlmostEqual(0.01, vmmxx.expense_ratio())
        self.assertEqual(2, len(vmmxx.get_lots()))

    @patch('yfinance.Ticker')
    def test_dict_ticker_with_expense(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                       'netExpenseRatio': 0.01}
        ticker.fast_info = {'lastPrice': 1.0}
        MockTicker.return_value = ticker

        vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0}, 0.03)
        lots = [assets.TaxLot('2012/12/12', 50, 1.0),
                assets.TaxLot('2013/12/12', 50, 0.9)]
        vmmxx.set_lots(lots)
        vmmxx.what_if(-10)
        vmmxx = assets.from_dict(assets.to_dict(vmmxx))
        self.assertEqual('VMMXX', vmmxx.short_name())
        self.assertEqual(100.0, vmmxx.shares())
        self.assertEqual({'All': 1.0}, vmmxx.class2ratio)
        self.assertAlmostEqual(90.0, vmmxx.adjusted_value())
        self.assertAlmostEqual(0.03, vmmxx.expense_ratio())
        self.assertEqual(2, len(vmmxx.get_lots()))

    @patch('yfinance.Ticker')
    def test_ticker_with_full_yfinance_response(self, MockTicker):
        ticker = MagicMock()
        ticker.info = {
            'phone': '800-523-1036',
            'longBusinessSummary': 'The fund manager (sniped)',
            'companyOfficers': [], 'executiveTeam': [], 'maxAge': 86400,
            'priceHint': 2, 'previousClose': 374.07, 'open': 376.17,
            'dayLow': 375.175, 'dayHigh': 377.48,
            'regularMarketPreviousClose': 374.07, 'regularMarketOpen': 376.17,
            'regularMarketDayLow': 375.175, 'regularMarketDayHigh': 377.48,
            'trailingPE': 24.116028, 'volume': 2826667,
            'regularMarketVolume': 2826667, 'averageVolume': 3009314,
            'averageVolume10days': 2825990, 'averageDailyVolume10Day': 2825990,
            'bid': 375.49, 'ask': 376.24, 'bidSize': 40, 'askSize': 320,
            'yield': 0.0106, 'totalAssets': 2322096979968,
            'fiftyTwoWeekLow': 310.4, 'fiftyTwoWeekHigh': 385.12,
            'allTimeHigh': 385.12, 'allTimeLow': 29.76, 'fulldayPrice': 376.0,
            'fulldayChange': 1.9299927, 'fulldayChangePercent': 0.51594424,
            'fiftyDayAverage': 378.4294, 'twoHundredDayAverage': 357.5395,
            'trailingAnnualDividendRate': 2.802,
            'trailingAnnualDividendYield': 0.0074905767, 'navPrice': 374.06,
            'currency': 'USD', 'tradeable': False, 'category': 'Large Blend',
            'ytdReturn': 12.58111, 'beta3Year': 1.03, 'fundFamily': 'Vanguard',
            'fundInceptionDate': 868233600,
            'legalType': 'Exchange Traded Fund',
            'threeYearAverageReturn': 0.21628611,
            'fiveYearAverageReturn': 0.1169208, 'quoteType': 'ETF',
            'symbol': 'VTI', 'language': 'en-US', 'region': 'US',
            'typeDisp': 'ETF', 'quoteSourceName': 'Nasdaq Real Time Price',
            'triggerable': True, 'customPriceAlertConfidence': 'HIGH',
            'postMarketPrice': 376.0, 'postMarketChange': 0.45999146,
            'regularMarketChange': 1.47,
            'regularMarketChangePercent': 0.392975,
            'regularMarketPrice': 375.54,
            'regularMarketDayRange': '375.175 - 377.48',
            'fullExchangeName': 'NYSEArca', 'financialCurrency': 'USD',
            'averageDailyVolume3Month': 3009314,
            'fiftyTwoWeekLowChange': 65.140015,
            'fiftyTwoWeekLowChangePercent': 0.2098583,
            'fiftyTwoWeekRange': '310.4 - 385.12',
            'fiftyTwoWeekHighChange': -9.579987,
            'fiftyTwoWeekHighChangePercent': -0.02487533,
            'fiftyTwoWeekChangePercent': 13.029158,
            'dividendYield': 1.06, 'trailingThreeMonthReturns': 1.35936,
            'trailingThreeMonthNavReturns': 1.35936,
            'netAssets': 2322096980000.0,
            'epsTrailingTwelveMonths': 15.572217,
            'sharesOutstanding': 743262976, 'bookValue': 139.506,
            'fiftyDayAverageChange': -2.8894043,
            'fiftyDayAverageChangePercent': -0.007635253,
            'twoHundredDayAverageChange': 18.000519,
            'twoHundredDayAverageChangePercent': 0.05034554,
            'netExpenseRatio': 0.03, 'priceToBook': 2.6919274,
            'sourceInterval': 15, 'exchangeDataDelayedBy': 0,
            'marketState': 'POST', 'corporateActions': [],
            'postMarketTime': 1792452484, 'regularMarketTime': 1792440000,
            'exchange': 'PCX', 'messageBoardId': 'finmb_6184536',
            'exchangeTimezoneName': 'America/New_York',
            'exchangeTimezoneShortName': 'EDT',
            'gmtOffSetMilliseconds': -14400000, 'market': 'us_market',
            'esgPopulated': False, 'cryptoTradeable': False,
            'hasPrePostMarketData': True,
            'firstTradeDateMilliseconds': 992611800000,
            'postMarketChangePercent': 0.122488,
            'shortName': 'Vanguard Morningstar Total Stoc',
            'longName': 'Vanguard Morningstar Total Stock Market ETF',
            'displayName': 'Morningstar Total Stock Mkt ETF',
            'trailingPegRatio': None}
        ticker.fast_info = {
            'currency': 'USD', 'dayHigh': 377.4800109863281,
            'dayLow': 375.17498779296875, 'exchange': 'PCX',
            'fiftyDayAverage': 378.4293994140625,
            'lastPrice': 375.5400085449219, 'lastVolume': 2826667,
            'marketCap': None, 'open': 376.1700134277344,
            'previousClose': 373.49, 'quoteType': 'ETF',
            'regularMarketPreviousClose': 374.07000732421875,
            'shares': None, 'tenDayAverageVolume': 2825990,
            'threeMonthAverageVolume': 3011555,
            'timezone': 'America/New_York',
            'twoHundredDayAverage': 357.5394985961914,
            'yearChange': 0.1302915652718365,
            'yearHigh': 385.1199951171875, 'yearLow': 310.3999938964844}
        MockTicker.return_value = ticker

        vti = assets.TickerAsset('VTI', 100.0, {'All': 1.0})
        self.assertEqual('Vanguard Morningstar Total Stock Market ETF',
                         vti.name())
        self.assertAlmostEqual(375.54, vti.price(), places=2)
        self.assertEqual(0.03, vti.expense_ratio())

    @patch('requests.Session.get')
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
            headers={'Referer': 'https://vanguard.com/'}, verify=False)

    @patch('requests.Session.get')
    def test_vanguard_funds_expense(self, mock_get):
        mock_res = MagicMock()

        with open(self.data_dir / 'profile.json') as data_file:
            mock_res.json.return_value = json.load(data_file)

        mock_get.return_value = mock_res

        fund = assets.VanguardFund(7555, 10, {'All': 1.0})
        self.assertEqual(0.01, fund.expense_ratio())
        mock_get.assert_called_once_with(
            'https://api.vanguard.com/rs/ire/01/pe/fund/7555/profile.json',
            headers={'Referer': 'https://vanguard.com/'}, verify=False)

    @patch('requests.Session.get')
    def test_vanguard_funds_value(self, mock_get):
        mock_res = MagicMock()

        with open(self.data_dir / 'price.json') as data_file:
            mock_res.json.return_value = json.load(data_file)
        mock_get.return_value = mock_res

        fund = assets.VanguardFund(7555, 10, {'All': 1.0})
        self.assertEqual(1166.6, fund.value())
        mock_get.assert_called_once_with(
            'https://api.vanguard.com/rs/ire/01/pe/fund/7555/price.json',
            headers={'Referer': 'https://vanguard.com/'}, verify=False)
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
    @patch('lakshmi.assets.VanguardFund.expense_ratio')
    def test_vangurd_fund_asset_to_table(self, mock_ratio, mock_price,
                                         mock_name):
        mock_price.return_value = 10.0
        mock_name.return_value = 'Vanguardy Fund'
        mock_ratio.return_value = 0.02

        fund = assets.VanguardFund(123, 100.0, {'All': 1.0})
        expected = [['Fund id:', '123'],
                    ['Name:', 'Vanguardy Fund'],
                    ['Asset Class Mapping:', 'All  100%'],
                    ['Value:', '$1,000.00'],
                    ['Expense ratio:', '0.02%'],
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

    @patch('lakshmi.assets.IBonds._InterestRates.get')
    @patch('lakshmi.assets.IBonds.value')
    def test_dict_i_bonds(self, mock_value, mock_get):
        mock_value.return_value = 11000
        mock_get.return_value = None
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
