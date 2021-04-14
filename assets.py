"""Standard asset types.

All these assets should implement the lakshmi.Asset top-level interface.
"""

import lakshmi
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
    self.yticker = ticker_obj(ticker)
    if self.yticker.info.get('regularMarketPrice') is None:
      raise NotFoundError('Cannot retrieve ticker ("{}") from Yahoo Finance'.format(
        ticker))
    
    self.shares = shares
    super().__init__(class2ratio)

  def Name(self):
    return self.yticker.info['shortName'].strip()

  def Value(self):
    return self.shares * self.yticker.info['regularMarketPrice']
