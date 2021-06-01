"""Classes to analyze the portfolio.

These classes are not meant to change the portfolio. They are used for
just analyzing the portfolio and output the results (if any).
"""

from abc import ABC, abstractmethod
import assets
import lakshmi
from table import Table

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
