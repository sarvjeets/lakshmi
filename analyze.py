"""Classes to analyze the portfolio.

These classes are not meant to change the portfolio. They are used for
just analyzing the portfolio and output the results (if any).
"""

from abc import ABC, abstractmethod
import assets
import lakshmi

class Analyzer(ABC):
  @abstractmethod
  @classmethod
  def FromDict(cls, d):
    """Factory method to return a class instance given a dictionary."""
    pass

  @abstractmethod
  def Analyze(self, portfolio):
    pass


#class TLHAnalyze(Analyzer):
#  """Tax loss harvesting opportunity analyzer.
#
#  This triggers a message with details of tax lots that could be sold to
#  harvest the losses.
#  """
#  def __init__(self, max_percentage, max_dollars):
#    """Triggers if a lot has lost more than max_percentage or the total loss
#    for a given asset exceeds max_dollars.
#    """
#    assert max_percentage > 0.0 and max_percentage < 1.0, (
#      'max_percetage should be between 0% and 100% (exclusive).')
#    self.max_percentage = max_percentage
#    if max_dollars:
#      assert max_dollars > 0, 'max_dollars should be positive.'
#    self.max_dollars = max_dollars
#
#  @classmethod
#  def FromDict(cls, d):
#    ret_obj = TLHAnalyze(d.pop('Max percentage'),
#                         d.pop('Max Dollars', None))
#    asset len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
#
#  def ReturnLotsToSell(self, tax_lots):
#    percent_lots = []
#    negative_lots = []
#    total_loss = 0.0
#
#    for lot in tax_lots:
#      pass
#
#  def Analyzer(self, portfolio):
#    pass
