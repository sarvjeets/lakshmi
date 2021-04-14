"""Standard asset types.

All these assets should implement the lakshmi.Asset top-level interface.
"""

import datetime
import lakshmi
import re
import requests
import yfinance


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


class TickerAsset(lakshmi.Asset):
  """An asset class representing a Ticket whose price can be pulled."""
  def __init__(self, ticker, shares, class2ratio, ticker_obj=yfinance.Ticker):
    self.ticker = ticker
    # Currently, we only pull data once when the object is created.
    self.yticker = ticker_obj(ticker)
    if self.yticker.info.get('regularMarketPrice') is None:
      raise NotFoundError('Cannot retrieve ticker ("{}") from Yahoo Finance'.format(
        ticker))

    self.shares = shares
    super().__init__(class2ratio)

  def Name(self):
    return self.yticker.info['longName'].strip()

  def Value(self):
    return self.shares * self.yticker.info['regularMarketPrice']

class VanguardFund(lakshmi.Asset):
  """An asset class representing Vanguard trust fund represented by an ID."""
  def __init__(self, fund_id, shares, class2ratio, requests_get=requests.get):
    self.fund_id = fund_id
    self.shares = shares
    super().__init__(class2ratio)
    headers = {'Referer': 'https://vanguard.com/'}
    url = 'https://api.vanguard.com/rs/ire/01/pe/fund/{}/{}.json'

    req = requests_get(url.format(fund_id, 'profile'), headers=headers)
    req.raise_for_status()  # Raise if error
    self.name = req.json()['fundProfile']['longName']

    req = requests_get(url.format(fund_id, 'price'), headers=headers)
    req.raise_for_status()  # Raise if error
    self.price = float(req.json()['currentPrice']['dailyPrice']['regular']['price'])

  def Name(self):
    return self.name

  def Value(self):
    return self.shares * self.price


class _TresuryBonds(lakshmi.Asset):
  def __init__(self, series, class2ratio):
    if series != 'EE' and series != 'I':
      raise lakshmi.ValidationError('Only I and EE series bonds are supported')

    self.series = series
    super().__init__(class2ratio)
    self.value = 0
    self.bonds = []

  def AddBond(self, issue_date, denom):
    rate, bond_value = self._GetBondInfo(issue_date, denom)
    self.value += bond_value
    self.bonds.append([issue_date, denom, rate, bond_value])

  def _GetBondInfo(self, issue_date, denom):
    scale = denom / 1000  # TD website doesn't support some denominations for electronic bonds.
    if self.series == 'EE':
      ## EE Bonds returned are half the value (I guess TD website assumes paper bonds)
      scale *= 2

    data = {
      "RedemptionDate" : datetime.datetime.now().strftime('%m/%Y'),
      "Series" : self.series,
      "Denomination" : '1000',
      "IssueDate" : issue_date,
      "btnAdd.x" : "CALCULATE"
    };

    req = requests.post('http://www.treasurydirect.gov/BC/SBCPrice', data=data)
    req.raise_for_status()

    # float(re.sub('\n|<[^>]+>', '', re.findall('\n<td>.*</td>', r.text)[7]))
    ret_vals = re.findall('\n<td>.*</td>', req.text)
    rate = re.sub('\n|<[^>]+>', '', ret_vals[6])
    value = float(re.sub('\n|\$|,|<[^>]+>', '', ret_vals[7]))

    return rate, value * scale

  def Value(self):
    return self.value

  def ListBonds(self):
    return self.bonds


class IBonds(_TresuryBonds):
  def __init__(self, class2ratio):
    super().__init__('I', class2ratio)

  def Name(self):
    return 'I Bonds'

class EEBonds(_TresuryBonds):
  def __init__(self, class2ratio):
    super().__init__('EE', class2ratio)

  def Name(self):
    return 'EE Bonds'
