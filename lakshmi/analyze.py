"""Classes to analyze the portfolio.

These classes are not meant to change the portfolio. They are used for
just analyzing the portfolio and output the results (if any).
"""

from abc import ABC, abstractmethod

from lakshmi.table import Table


# TODO(sarvjeets): This is not needed/used anywhere. Consider removing it.
class Analyzer(ABC):
    @abstractmethod
    def analyze(self, portfolio):
        pass


class TLH(Analyzer):
    """Tax loss harvesting opportunity analyzer.

    This triggers a message with details of tax lots that could be sold to
    harvest the losses.
    """

    def __init__(self, max_percentage, max_dollars=None):
        """Triggers if a lot has lost more than max_percentage or the total loss
        for a given asset exceeds max_dollars.

        Args:
            max_percentage: A float representing the max percentage loss after
            which a lot can be harvested.
            max_dollars: A float representing the max amount of loss (in
            dollars) for one or more lots (of the same security), beyond which
            we should recommend selling all the lots that are below their
            cost basis.
        """
        assert max_percentage > 0.0 and max_percentage < 1.0, (
            'max_percetage should be between 0% and 100% (exclusive).')
        self.max_percentage = max_percentage
        if max_dollars:
            assert max_dollars > 0, 'max_dollars should be positive.'
        self.max_dollars = max_dollars

    def _return_lots_to_sell(self, price, tax_lots):
        """Helper function that returns which lots to harvest.

        Args:
            price: The current price of the security.
            tax_lots: A list of lakshmi.assets.TaxLot (all belonging
            to the same security).

        Returns: A list of [lot date, loss in dollar, loss in percent]
        that could be loss harvested.
        """
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

    def analyze(self, portfolio):
        """Returns which lots can be tax loss harvested from a portfolio.

        Args:
            portfolio: A lakshmi.Portfolio object representing a portfolio.

        Returns: A lakshmi.table.Table object with tax lots to harvest with
        columns corespnding to 'Account', 'Asset', 'Date', 'Loss' and 'Loss%'.
        """
        ret_val = Table(
            5,
            headers=['Account', 'Asset', 'Date', 'Loss', 'Loss%'],
            coltypes=['str', 'str', 'str', 'dollars', 'percentage'])
        for account in portfolio.accounts():
            for asset in account.assets():
                if hasattr(asset, 'get_lots') and asset.get_lots():
                    for lot in self._return_lots_to_sell(
                            asset.price(), asset.get_lots()):
                        ret_val.add_row(
                            [account.name(), asset.short_name()] + lot)
        return ret_val


class BandRebalance(Analyzer):
    """Triggers if portfolio asset class targets are outside the bands
    specified. This considers an asset class outside bound if the absolute
    difference in percentage allocation is more than max_abs_percent different
    from target allocation or more than max_relative_percent different from the
    target allocation.

    A popular version is the 5/25 band based rebalancing rule. For more
    information, please see 5/25 on:
    https://www.bogleheads.org/wiki/Rebalancing
    """

    def __init__(self, max_abs_percent=0.05, max_relative_percent=0.25):
        """Constructor to set the bands. An asset class is considered outside
        the rebalance bands if the differnt between the desired and actual
        ratio of that asset class exceeds the lessor of max absolute or max
        relative percentage.

        Args:
            max_abs_percent: A float (ratio) representing the maximum absolute
            percent that an asset can deviate before it's considered outside
            the rebalancing band.
            max_relative_percent: A float (ratio) representing the maximum
            relative percent that an asset can deviate before it's considered
            outside the rebalancing band.
        """
        assert max_abs_percent > 0 and max_abs_percent < 1.0
        assert max_relative_percent > 0 and max_relative_percent < 1.0
        self.max_abs_percent = max_abs_percent
        self.max_relative_percent = max_relative_percent

    def analyze(self, portfolio):
        """Returns asset classes that are outside the rebalancing bands.

        Args:
            portfolio: A lakshmi.Portfolio object representing the portfolio
            that is being analyzed.

        Returns: A lakshmi.table.Table object with columns representing
        Asset Class, Actual % of asset class in portfolio, Desired % of asset
        class in the portfolio, Value in dollars of the asset class and the
        difference between Desired and actual dollar values.
        """
        aa = portfolio.asset_allocation(portfolio.asset_classes.leaves())
        headers = ['Class', 'Actual%', 'Desired%', 'Value', 'Difference']
        assert headers == aa.headers()
        ret_val = Table(
            5,
            headers,
            ['str', 'percentage', 'percentage', 'dollars', 'delta_dollars'])
        for row in aa.list():
            abs_percent = abs(row[1] - row[2])
            rel_percent = abs_percent / row[2] if row[2] != 0 else 0
            if (
                abs_percent >= self.max_abs_percent
                or rel_percent >= self.max_relative_percent
            ):
                ret_val.add_row(row)

        return ret_val
