"""Standard asset types.

All these assets should implement the lakshmi.Asset top-level interface.
"""

import datetime
import lakshmi
import re
import requests
import yfinance

from cache import cache, Cacheable


class NotFoundError(Exception):
  pass


class SimpleAsset(lakshmi.Asset):
  def __init__(self, name, value, class2ratio):
    self.name = name
    self.value = value
    super().__init__(class2ratio)

  def Value(self):
    return self.value

  def Name(self):
    return self.name


class TickerAsset(lakshmi.Asset, Cacheable):
  """An asset class representing a Ticket whose price can be pulled."""
  def __init__(self, ticker, shares, class2ratio):
    self.ticker = ticker
    # Currently, we only pull data once when the object is created.
    self.yticker = yfinance.Ticker(ticker)
    self.shares = shares
    super().__init__(class2ratio)

  def Key(self):
    return self.ticker

  @cache(1)
  def Name(self):
    if self.yticker.info.get('longName') is None:
      raise NotFoundError('Cannot retrieve ticker ("{}") from Yahoo Finance'.format(
        self.ticker))
    return self.yticker.info['longName']

  def Value(self):
    return self.shares * self.Price()

  @cache(1)
  def Price(self):
    if self.yticker.info.get('regularMarketPrice') is None:
      raise NotFoundError('Cannot retrieve ticker ("{}") from Yahoo Finance'.format(
        self.ticker))
    return self.yticker.info['regularMarketPrice']


class VanguardFund(lakshmi.Asset, Cacheable):
  """An asset class representing Vanguard trust fund represented by an ID."""
  def __init__(self, fund_id, shares, class2ratio):
    self.fund_id = fund_id
    self.shares = shares
    super().__init__(class2ratio)

  def Key(self):
    return str(self.fund_id)

  @cache(365)  # Name changes are very rare.
  def Name(self):
    req = requests.get(
      'https://api.vanguard.com/rs/ire/01/pe/fund/{}/profile.json'.format(self.fund_id),
      headers={'Referer': 'https://vanguard.com/'})
    req.raise_for_status()  # Raise if error
    return req.json()['fundProfile']['longName']

  @cache(1)
  def Price(self):
    req = requests.get(
      'https://api.vanguard.com/rs/ire/01/pe/fund/{}/price.json'.format(self.fund_id),
      headers={'Referer': 'https://vanguard.com/'})
    req.raise_for_status()  # Raise if error
    return float(req.json()['currentPrice']['dailyPrice']['regular']['price'])

  def Value(self):
    return self.shares * self.Price()


class _TreasuryBonds(lakshmi.Asset):
  class Bond(Cacheable):
    """A class representing individual I or EE Bond."""
    def __init__(self, series, issue_date, denom, redemption_date):
      self.series = series
      self.issue_date = issue_date
      self.denom = denom
      self.redemption_date = redemption_date

    def Key(self):
      return '{}_{}_{}_{}'.format(
        self.series,
        self.issue_date.replace('/', '.'),
        self.denom,
        self.redemption_date.replace('/', '.'))

    @cache(32)  # The value of a Bond doesn't change in a month.
    def _GetBondInfo(self):
      scale = self.denom / 1000.0  # TD website doesn't support some denominations for electronic bonds.
      if self.series == 'EE':
        # EE Bonds returned are half the value (I guess TD website assumes paper bonds)
        scale *= 2

      data = {
        'RedemptionDate' : self.redemption_date,
        'Series' : self.series,
        'Denomination' : '1000',
        'IssueDate' : self.issue_date,
        'btnAdd.x' : 'CALCULATE'
      };

      req = requests.post('http://www.treasurydirect.gov/BC/SBCPrice', data=data)
      req.raise_for_status()

      # float(re.sub('\n|<[^>]+>', '', re.findall('\n<td>.*</td>', r.text)[7]))
      ret_vals = re.findall('\n<td>.*</td>', req.text)
      rate = re.sub('\n|<[^>]+>', '', ret_vals[6])
      value = float(re.sub('\n|\$|,|<[^>]+>', '', ret_vals[7]))
      return rate, scale * value

    def Value(self):
      unused_rate, value = self._GetBondInfo()
      return value

    def Rate(self):
      rate, unused_value = self._GetBondInfo()
      return rate

    def AsList(self):
      rate, value = self._GetBondInfo()
      return [self.issue_date, self.denom, rate, value]

  def __init__(self, series, class2ratio):
    self.series = series
    super().__init__(class2ratio)
    self.value = 0
    self.bonds = []
    self.redemption_date = datetime.datetime.now().strftime('%m/%Y')

  def AddBond(self, issue_date, denom):
    self.bonds.append(
      self.Bond(self.series, issue_date, denom, self.redemption_date))
    return self

  def Value(self):
    value = 0.0
    for bond in self.bonds:
      value += bond.Value()
    return value

  def ListBonds(self):
    ret_val = []
    for bond in self.bonds:
      ret_val.append(bond.AsList())
    return ret_val


class IBonds(_TreasuryBonds):
  def __init__(self, class2ratio):
    super().__init__('I', class2ratio)

  def Name(self):
    return 'I Bonds'

class EEBonds(_TreasuryBonds):
  def __init__(self, class2ratio):
    super().__init__('EE', class2ratio)

  def Name(self):
    return 'EE Bonds'
