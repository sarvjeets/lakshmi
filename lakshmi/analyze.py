"""Classes to analyze the portfolio.

These classes are not meant to change the portfolio. They are used for
just analyzing the portfolio and output the results (if any).
"""

from abc import ABC, abstractmethod
from lakshmi.table import Table

class Analyzer(ABC):
  @abstractmethod
  def Analyze(self, portfolio):
    pass


class TLHAnalyze(Analyzer):
  """Tax loss harvesting opportunity analyzer.

  This triggers a message with details of tax lots that could be sold to
  harvest the losses.
  """
  def __init__(self, max_percentage, max_dollars=None):
    """Triggers if a lot has lost more than max_percentage or the total loss
    for a given asset exceeds max_dollars.
    """
    assert max_percentage > 0.0 and max_percentage < 1.0, (
      'max_percetage should be between 0% and 100% (exclusive).')
    self.max_percentage = max_percentage
    if max_dollars:
      assert max_dollars > 0, 'max_dollars should be positive.'
    self.max_dollars = max_dollars

  def _ReturnLotsToSell(self, price, tax_lots):
    percent_lots = []
    negative_lots = []
    total_loss = 0.0

    for lot in tax_lots:
      loss = (lot.unit_cost - price) * lot.quantity
      loss_percent = (lot.unit_cost - price) / lot.unit_cost
      if loss > 0:
        negative_lots.append([lot.date, loss, loss_percent])
        total_loss += loss
      if loss_percent > self.max_percentage:
        percent_lots.append([lot.date, loss, loss_percent])

    if self.max_dollars is not None and total_loss > self.max_dollars:
      return negative_lots
    else:
      return percent_lots

  def Analyze(self, portfolio):
    ret_val = Table(
      5,
      headers = ['Account', 'Asset', 'Date', 'Loss', 'Loss%'],
      coltypes = ['str', 'str', 'str', 'dollars', 'percentage'])
    for account in portfolio.Accounts():
      for asset in account.Assets():
        if hasattr(asset, 'tax_lots') and asset.tax_lots:
          assert hasattr(asset, 'Price'), 'Asset has tax lots but no Price'
          price = asset.Price()
          for lot in self._ReturnLotsToSell(price, asset.tax_lots):
            ret_val.AddRow([account.Name(), asset.ShortName()] + lot)
    return ret_val

class BandRebalance(Analyzer):
  """Triggers if portfolio asset class targets are outside the bands
  specified. This considers an asset class outside bound if the
  absolute difference in percentage allocation is more than max_abs_percent
  different from target allocation or more than max_relative_percent
  different from the target allocation."""
  def __init__(self, max_abs_percent=0.05, max_relative_percent=0.25):
    assert max_abs_percent > 0 and max_abs_percent < 1.0
    assert max_relative_percent > 0 and max_relative_percent < 1.0
    self.max_abs_percent = max_abs_percent
    self.max_relative_percent = max_relative_percent

  def Analyze(self, portfolio):
    aa = portfolio.AssetAllocation(portfolio.asset_classes.Leaves())
    headers = ['Class', 'Actual%', 'Desired%', 'Value', 'Difference']
    assert headers == aa.Headers()
    ret_val = Table(
      5,
      headers,
      ['str', 'percentage', 'percentage', 'dollars', 'delta_dollars'])
    for row in aa.List():
      abs_percent = abs(row[1] - row[2])
      rel_percent = abs_percent / row[2] if row[2] != 0 else 0
      if (abs_percent >= self.max_abs_percent or
          rel_percent >= self.max_relative_percent):
        ret_val.AddRow(row)

    return ret_val