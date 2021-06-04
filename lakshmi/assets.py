"""Implementation of standard asset types."""

from abc import ABC, abstractmethod
from lakshmi.cache import cache, Cacheable
import datetime
import re
import requests
import yfinance


def ToDict(asset):
  return {asset.__class__.__name__ : asset.ToDict()}


def FromDict(d):
  keys = list(d.keys())
  assert len(keys) == 1
  class_name = keys[0]

  classes = [ManualAsset, TickerAsset, VanguardFund, IBonds, EEBonds]
  for c in classes:
    if c.__name__ == class_name:
      return c.FromDict(d.pop(class_name))

  assert False, 'Class {} not found.'.format(class_name)


class Asset(ABC):
  """Class representing an asset (fund, ETF, cash, etc.)."""
  def __init__(self, class2ratio):
    """
    Argments:
      class2ratio: Dict of class_name -> ratio. 0 < Ratio <= 1.0
    """
    self._delta = 0
    self.class2ratio = class2ratio

    total = 0
    for ratio in class2ratio.values():
      assert ratio >= 0.0 and ratio <= 1.0, (
        'Bad Class ratio provided to Asset ({})'.format(ratio))
      total += ratio

    assert abs(total - 1.0) < 1e-6, (
      'Total allocation to classes must be 100% (actual = {}%)'.format(
          round(total*100)))

  def ToDict(self):
    """Encodes this class into a dictionary.

    This method for non-abstract Asset classes encodes all data.
    This method for abstract Asset classes only encodes non-constructor data.
    """
    if self._delta != 0:
      return {'What if': self._delta}
    return dict()

  def FromDict(self, d):
    """Reverse of ToDict.

    This method for non-abstract Asset classes is a factory method.
    This method for abstract Asset classes decodes non-constructor data (if any).
    """
    self.WhatIf(d.pop('What if', 0))
    return self

  def WhatIf(self, delta):
    self._delta += delta

  def AdjustedValue(self):
    return self.Value() + self._delta

  @abstractmethod
  def Value(self):
    pass

  @abstractmethod
  def Name(self):
    pass

  @abstractmethod
  def ShortName(self):
    pass


class ManualAsset(Asset):
  def __init__(self, name, value, class2ratio):
    self.name = name
    self.value = value
    super().__init__(class2ratio)

  def ToDict(self):
    d = {'Name': self.name,
         'Value': self.value,
         'Asset Mapping': self.class2ratio}
    d.update(super().ToDict())
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = ManualAsset(d.pop('Name'),
                          d.pop('Value', 0),
                          d.pop('Asset Mapping'))
    Asset.FromDict(ret_obj, d)
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def Value(self):
    return self.value

  def Name(self):
    return self.name

  def ShortName(self):
    return self.name


class TaxLot:
  """Class to represent a single tax lot for an Asset."""
  def __init__(self, date, quantity, unit_cost):
    # Do some sanity check.
    date_pattern = re.compile('\d{4}/\d{2}/\d{2}')
    assert date_pattern.match(date), 'Tax lot dates should be in format YYYY/MM/DD'

    self.date = date
    self.quantity = quantity
    self.unit_cost = unit_cost

  def ToDict(self):
    return {'Date': self.date,
            'Quantity': self.quantity,
            'Unit Cost': self.unit_cost}

  @classmethod
  def FromDict(cls, d):
    ret_obj = TaxLot(d.pop('Date'), d.pop('Quantity'), d.pop('Unit Cost'))
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj


class TradedAsset(Asset):
  """An abstract class representing an asset with units and per unit price."""
  def __init__(self, shares, class2ratio):
    self.shares = shares
    self.tax_lots = None
    super().__init__(class2ratio)

  def ToDict(self):
    d = dict()
    if self.tax_lots:
      d.update({'Tax Lots': [lot.ToDict() for lot in self.tax_lots]})
    d.update(super().ToDict())
    return d

  def FromDict(self, d):
    super().FromDict(d)
    if 'Tax Lots' not in d:
      return
    tax_lots_list = [TaxLot.FromDict(lot_dict) for lot_dict in d.pop('Tax Lots')]
    self.SetLots(tax_lots_list)
    return self

  def SetLots(self, tax_lots_list):
    sum_lots = sum([t.quantity for t in tax_lots_list])
    assert abs(sum_lots - self.shares) < 1e-6, (
      'Lots provided should sum up to ' + str(self.shares))
    self.tax_lots = tax_lots_list
    return self

  def Value(self):
    return self.shares * self.Price()

  # This class inherits abstract methods Name & ShortName from Asset.

  @abstractmethod
  def Price(self):
    pass


class NotFoundError(Exception):
  pass


class TickerAsset(TradedAsset, Cacheable):
  """An asset class representing a Ticker whose price can be pulled."""
  def __init__(self, ticker, shares, class2ratio):
    self.ticker = ticker
    self.yticker = yfinance.Ticker(ticker)
    super().__init__(shares, class2ratio)

  def ToDict(self):
    d = {'Ticker': self.ticker,
         'Shares': self.shares,
         'Asset Mapping': self.class2ratio}
    d.update(super().ToDict())
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = TickerAsset(d.pop('Ticker'), d.pop('Shares'), d.pop('Asset Mapping'))
    TradedAsset.FromDict(ret_obj, d)
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def CacheKey(self):
    return self.ticker

  @cache(1)
  def Name(self):
    if self.yticker.info.get('longName') is None:
      raise NotFoundError('Cannot retrieve ticker ("{}") from Yahoo Finance'.format(
        self.ticker))
    return self.yticker.info['longName']

  def ShortName(self):
    return self.ticker

  @cache(1)
  def Price(self):
    if self.yticker.info.get('regularMarketPrice') is None:
      raise NotFoundError('Cannot retrieve ticker ("{}") from Yahoo Finance'.format(
        self.ticker))
    return self.yticker.info['regularMarketPrice']


class VanguardFund(TradedAsset, Cacheable):
  """An asset class representing Vanguard trust fund represented by a numeric ID."""
  def __init__(self, fund_id, shares, class2ratio):
    self.fund_id = fund_id
    super().__init__(shares, class2ratio)

  def ToDict(self):
    d = {'Fund Id': self.fund_id,
         'Shares': self.shares,
         'Asset Mapping': self.class2ratio}
    d.update(super().ToDict())
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = VanguardFund(d.pop('Fund Id'), d.pop('Shares'), d.pop('Asset Mapping'))
    TradedAsset.FromDict(ret_obj, d)
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def CacheKey(self):
    return str(self.fund_id)

  @cache(365)  # Name changes are very rare.
  def Name(self):
    req = requests.get(
      'https://api.vanguard.com/rs/ire/01/pe/fund/{}/profile.json'.format(self.fund_id),
      headers={'Referer': 'https://vanguard.com/'})
    req.raise_for_status()  # Raise if error
    return req.json()['fundProfile']['longName']

  def ShortName(self):
    return str(self.fund_id)

  @cache(1)
  def Price(self):
    req = requests.get(
      'https://api.vanguard.com/rs/ire/01/pe/fund/{}/price.json'.format(self.fund_id),
      headers={'Referer': 'https://vanguard.com/'})
    req.raise_for_status()  # Raise if error
    return float(req.json()['currentPrice']['dailyPrice']['regular']['price'])


class _TreasuryBonds(Asset):
  class Bond(Cacheable):
    """A class representing individual I or EE Bond."""
    def __init__(self, series, issue_date, denom):
      self.series = series
      self.issue_date = issue_date
      self.denom = denom
      self.redemption_date = datetime.datetime.now().strftime('%m/%Y')

    def CacheKey(self):
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
    self.bonds = []

  def ToDict(self):
    d = {}
    d['Bonds'] = []
    for bond in self.bonds:
      d['Bonds'].append({'Issue Date': bond.issue_date, 'Denomination': bond.denom})
    d.update(super().ToDict())
    return d

  def FromDict(self, d):
    for bond in d.pop('Bonds'):
      self.AddBond(bond.pop('Issue Date'), bond.pop('Denomination'))
      assert len(bond) == 0, 'Extra attributes found: ' + str(list(bond.keys()))
    Asset.FromDict(self, d)
    return self

  def AddBond(self, issue_date, denom):
    self.bonds.append(self.Bond(self.series, issue_date, denom))
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

  def ToDict(self):
    d = {'Asset Mapping': self.class2ratio}
    d.update(super().ToDict())
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = IBonds(d.pop('Asset Mapping'))
    _TreasuryBonds.FromDict(ret_obj, d)
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def Name(self):
    return 'I Bonds'

  def ShortName(self):
    return self.Name()


class EEBonds(_TreasuryBonds):
  def __init__(self, class2ratio):
    super().__init__('EE', class2ratio)

  def ToDict(self):
    d = {'Asset Mapping': self.class2ratio}
    d.update(super().ToDict())
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = EEBonds(d.pop('Asset Mapping'))
    _TreasuryBonds.FromDict(ret_obj, d)
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def Name(self):
    return 'EE Bonds'

  def ShortName(self):
    return self.Name()