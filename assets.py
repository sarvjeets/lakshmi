"""Standard asset types.

All these assets should implement the lakshmi.Asset top-level interface.
"""

import lakshmi
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
