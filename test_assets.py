#!/usr/bin/python3

import assets
import unittest
from unittest.mock import MagicMock, patch
import cache

class AssetsTest(unittest.TestCase):
  def setUp(self):
    cache.CACHE_DIR = None  # Disable caching.

  @patch('yfinance.Ticker')
  def testBadTicker(self, MockTicker):
    bad_ticker = MagicMock()
    bad_ticker.info = {}
    MockTicker.return_value = bad_ticker

    ticker_asset = assets.TickerAsset('bad', 10, {'All': 1.0})

    with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
      ticker_asset.Name()
    with self.assertRaisesRegex(assets.NotFoundError, 'Cannot retrieve ticker'):
      ticker_asset.Value()

    MockTicker.assert_called_once_with('bad')

  @patch('yfinance.Ticker')
  def testGoodTicker(self, MockTicker):
    ticker = MagicMock()
    ticker.info = {'longName': 'Vanguard Cash Reserves Federal',
                   'regularMarketPrice': 1.0}
    MockTicker.return_value = ticker

    vmmxx = assets.TickerAsset('VMMXX', 100.0, {'All': 1.0})
    self.assertAlmostEqual(100.0, vmmxx.Value())
    self.assertEqual('Vanguard Cash Reserves Federal', vmmxx.Name())
    self.assertEqual('VMMXX', vmmxx.ShortName())

    MockTicker.assert_called_once_with('VMMXX')

  @patch('requests.get')
  def testVanguardFundsName(self, MockGet):
    MockReq = MagicMock()
    MockReq.json.return_value = {"fundProfile":{"fundId":"1884","citFundId":"7555","instrumentId":27075102,"shortName":"Inst Tot Bd Mkt Ix Tr","longName":"Vanguard Institutional Total Bond Market Index Trust","inceptionDate":"2016-06-24T00:00:00-04:00","newspaperAbbreviation":"VanTBdMIxInsSel     ","style":"Bond Funds","type":"Bond Funds","category":"Intermediate-Term Bond","customizedStyle":"Bond - Inter-term Investment","fixedIncomeInvestmentStyleId":"2","fixedIncomeInvestmentStyleName":"Intermediate-term Treasury","secDesignation":"","maximumYearlyInvestment":"","expenseRatio":"0.0100","expenseRatioAsOfDate":"2020-04-28T00:00:00-04:00","isInternalFund":True,"isExternalFund":False,"isMutualFund":True,"isETF":False,"isVLIP":False,"isVVAP":False,"is529":False,"hasAssociatedInvestorFund":True,"hasMoreThan1ShareClass":True,"isPESite":True,"fundFact":{"isActiveFund":True,"isClosed":False,"isClosedToNewInvestors":False,"isFundOfFunds":False,"isMSCIIndexedFund":False,"isIndex":True,"isLoadFund":False,"isMoneyMarket":False,"isBond":True,"isBalanced":False,"isStock":False,"isInternational":False,"isMarketNeutralFund":False,"isInternationalStockFund":False,"isInternationalBalancedFund":False,"isDomesticStockFund":False,"isTaxable":True,"isTaxExempt":False,"isTaxManaged":False,"isTaxableBondFund":True,"isTaxExemptBondFund":False,"isTaxExemptMoneyMarketFund":False,"isTaxSensitiveFund":True,"isSpecialtyStockFund":False,"isHybridFund":False,"isGlobal":False,"isManagedPayoutFund":False,"isGNMAFund":False,"isInvestorShare":False,"isAdmiralShare":False,"isInstitutionalShare":False,"isAdmiralFund":False,"isStableValueFund":False,"isCompanyStockFund":False,"isREITFund":False,"isVariableInsuranceFund":False,"isComingledTrustFund":False,"isConvertibleFund":False,"isAssetAllocationFund":False,"isStateMunicipalBond":False,"isNationalMunicipalBond":False,"isQualifiedOnly":False,"isPreciousMetalsFund":False,"mIsVIPSFund":False,"isSectorSpecific":False,"hasOtherIndex":False,"isTargetRetirementFund":False,"isRetirementSavingsTrustFund":False,"isNon40ActFund":True,"isUnfundedFund":False,"isCreditSuisseFund":False,"isKaiserFund":False,"isFundAccessFund":False,"isFundTransferableToVGI":False,"hasTransactionFee":False,"isNTFFund":False,"hasMoreThan1ShareClass":False,"isOpenToFlagship":False,"isOpenToFlagshipPlus":False,"isCitFund":True,"isAcctType15Fund":False,"isEtfOfEtfs":False,"isStandaloneEtf":False},"associatedFundIds":{"investorFundId":"0084","admiralFundId":"0584","etfFundId":"0928","institutionalFundId":"0222","institutionalPlusFundId":"0850"},"fundCategory":{"customizedHighCategoryName":"Bond - Inter-term Investment","high":{"type":"HIGH","id":3,"name":"Bond Funds"},"mid":{"type":"MID","id":31,"name":"Bond Funds"},"low":{"type":"LOW","id":3105,"name":"Intermediate-Term Bond"}},"largeTransactionAmount":25000000,"qualifiedTransactionAmount":50000000,"minimumInitialInvestment":3.0E9,"signalFundFlag":False},"historicalReturn":{"percent":"8.85","startDate":"1972-12-31T00:00:00-05:00","endDate":"2011-12-31T00:00:00-05:00"}}
    MockGet.return_value = MockReq

    fund = assets.VanguardFund(7555, 10, {'All': 1.0})
    self.assertEqual('Vanguard Institutional Total Bond Market Index Trust',
                     fund.Name())
    self.assertEqual('7555', fund.ShortName())
    MockGet.assert_called_once_with(
      'https://api.vanguard.com/rs/ire/01/pe/fund/7555/profile.json',
      headers={'Referer': 'https://vanguard.com/'})

  @patch('requests.get')
  def testVanguardFundsValue(self, MockGet):
    MockReq = MagicMock()
    MockReq.json.return_value = {"currentPrice":{"yield":{"hasDisclaimer":False},"dailyPrice":{"regular":{"asOfDate":"2021-04-15T00:00:00-04:00","price":"116.66","priceChangeAmount":"0.52","priceChangePct":"0.45","currOrPrmlFlag":"CURR","currOrPrmlValue":"Price"}},"highLow":{"regular":{"highDate":"2020-08-06T00:00:00-04:00","highPrice":"120.210000","lowDate":"2021-03-18T00:00:00-04:00","lowPrice":"114.970000","spreadPrice":"5.240000","spreadPct":"4.56","hasMultipleHighDates":False,"hasMultipleLowDates":False,"highDates":[{}],"lowDates":[{}]}}},"historicalPrice":{"isMultiYears":False,"nav":[{"item":[{"asOfDate":"2021-04-15T00:00:00-04:00","price":"116.66"},{"asOfDate":"2021-04-14T00:00:00-04:00","price":"116.14"},{"asOfDate":"2021-04-13T00:00:00-04:00","price":"116.24"},{"asOfDate":"2021-04-12T00:00:00-04:00","price":"115.93"},{"asOfDate":"2021-04-09T00:00:00-04:00","price":"116.01"},{"asOfDate":"2021-04-08T00:00:00-04:00","price":"116.11"},{"asOfDate":"2021-04-07T00:00:00-04:00","price":"115.90"},{"asOfDate":"2021-04-06T00:00:00-04:00","price":"115.99"},{"asOfDate":"2021-04-05T00:00:00-04:00","price":"115.67"},{"asOfDate":"2021-04-01T00:00:00-04:00","price":"115.86"}]}],"marketPrice":[{}]}}
    MockGet.return_value = MockReq

    fund = assets.VanguardFund(7555, 10, {'All': 1.0})
    self.assertEqual(1166.6, fund.Value())
    MockGet.assert_called_once_with(
      'https://api.vanguard.com/rs/ire/01/pe/fund/7555/price.json',
      headers={'Referer': 'https://vanguard.com/'})

  @patch('datetime.datetime')
  @patch('requests.post')
  def testIBonds(self, MockPost, MockDate):
    MockReq = MagicMock()
    MockReq.text = """Stuff
    <td>More stuff</td>
<div id="bogus">
<td class="lft">NA</td>
<td class="se">I</td>
<td>$1,000</td>
<td>03/2020</td>
<td>05/2021</td>
<td>03/2050</td>
<td>$1,000.00</td>
<td>$15.60</td>
<td>1.88%</td>
<td><strong>$1,015.60</strong></td>
<td class="nt"><a href="#nte">P5</a></td>
<td class="rgt"><input class="linkbutton" type="submit" name="btnDel0.x" value="REMOVE" /></td>
</tr>
... and more stuff
"""
    MockPost.return_value = MockReq
    MockDate.now.strftime.return_value = '04/2021'

    ibonds = assets.IBonds({'All': 1.0})
    ibonds.AddBond('03/2020', 10000)

    MockPost.asset_called_once_with(
      'http://www.treasurydirect.gov/BC/SBCPrice',
      data = {
        'RedemptionDate' : '04/2021',
        'Series' : 'I',
        'Denomination' : '1000',
        'IssueDate' : '03/2020',
        'btnAdd.x' : 'CALCULATE'})

    self.assertEqual('I Bonds', ibonds.Name())
    self.assertEqual('I Bonds', ibonds.ShortName())
    self.assertAlmostEqual(10156.0, ibonds.Value())
    self.assertEqual(1, len(ibonds.ListBonds()))
    self.assertEqual(4, len(ibonds.ListBonds()[0]))
    self.assertEqual('03/2020', ibonds.ListBonds()[0][0])
    self.assertEqual(10000, ibonds.ListBonds()[0][1])
    self.assertEqual('1.88%', ibonds.ListBonds()[0][2])
    self.assertAlmostEqual(10156.0, ibonds.ListBonds()[0][3])

  @patch('datetime.datetime')
  @patch('requests.post')
  def testEEBonds(self, MockPost, MockDate):
    MockReq = MagicMock()
    MockReq.text = """Stuff
    <td>More stuff</td>
<div id="bogus">
<td class="lft">NA</td>
<td class="se">EE</td>
<td>$1,000</td>
<td>03/2020</td>
<td>05/2021</td>
<td>03/2050</td>
<td>$500.00</td>
<td>$0.40</td>
<td>0.10%</td>
<td><strong>$500.40</strong></td>
<td class="nt"><a href="#nte">P5</a></td>
<td class="rgt"><input class="linkbutton" type="submit" name="btnDel0.x" value="REMOVE" /></td>
</tr>
... and more stuff
"""
    MockPost.return_value = MockReq
    MockDate.now.strftime.return_value = '04/2021'

    eebonds = assets.EEBonds({'All': 1.0})
    eebonds.AddBond('03/2020', 10000)

    MockPost.asset_called_once_with(
      'http://www.treasurydirect.gov/BC/SBCPrice',
      data = {
        'RedemptionDate' : '04/2021',
        'Series' : 'EE',
        'Denomination' : '500',
        'IssueDate' : '03/2020',
        'btnAdd.x' : 'CALCULATE'})

    self.assertEqual('EE Bonds', eebonds.Name())
    self.assertEqual('EE Bonds', eebonds.ShortName())
    self.assertAlmostEqual(10008.0, eebonds.Value())
    self.assertEqual(1, len(eebonds.ListBonds()))
    self.assertEqual(4, len(eebonds.ListBonds()[0]))
    self.assertEqual('03/2020', eebonds.ListBonds()[0][0])
    self.assertEqual(10000, eebonds.ListBonds()[0][1])
    self.assertEqual('0.10%', eebonds.ListBonds()[0][2])
    self.assertAlmostEqual(10008.0, eebonds.ListBonds()[0][3])


if __name__ == '__main__':
  unittest.main()
