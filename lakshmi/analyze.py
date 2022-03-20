"""Classes to analyze the portfolio.

These classes are not meant to change the portfolio. They are used for
just analyzing the portfolio and output the results (if any).
"""

from abc import ABC, abstractmethod

import numpy as np

from lakshmi.table import Table
from lakshmi.utils import format_money


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


class _Solver:
    """Internal class to help allocate cash to portfolio (see next class).

    TODO: Add actual maths.
    """

    def __init__(self, aa, assets, cash, total):
        self.aa = aa
        self.assets = assets
        self.total = total
        self.cash = cash

    def desired_ratio(self, asset_class):
        return self.aa[asset_class][0]

    def money(self, asset_class):
        return self.aa[asset_class][1]

    def derivative(self, i):
        # The actual derivative has (2/total_money) extra term, but as it is
        # common in all assets, we ignore it.
        sum = 0
        for ac in self.assets[i].class2ratio.keys():
            rel_ratio = (self.money(ac) / (self.desired_ratio(ac) * self.total)
                         - 1)
            sum += rel_ratio * (self.assets[i].class2ratio[ac]
                                / self.desired_ratio(ac))
        return sum

    def compute_delta(self, i, target_derivative):
        term1 = term2 = term3 = 0
        for ac in self.assets[i].class2ratio.keys():
            term1 += self.assets[i].class2ratio[ac] / self.desired_ratio(ac)
            term2 += (self.assets[i].class2ratio[ac]
                      * self.money(ac)
                      / self.desired_ratio(ac) ** 2)
            term3 += (self.assets[i].class2ratio[ac] ** 2
                      / self.desired_ratio(ac) ** 2)
        ans = (self.total * (target_derivative + term1) - term2) / term3
        assert (ans >= 0) ^ (self.cash < 0)  # i.e. they have same sign.
        return ans

    def sorted_index_and_derivatives(self):
        index_and_derivative = [
            (i, self.derivative(i)) for i in range(len(self.assets))]
        # Sorted index gives a prioritized list of assets to which the money
        # should be added (if cash > 0) or removed from (if cash < 0).
        sorted_index_derivative = sorted(index_and_derivative,
                                         key=lambda x: x[1],
                                         reverse=(self.cash < 0))
        return ([x[0] for x in sorted_index_derivative],
                [x[1] for x in sorted_index_derivative])

    def update_aa(self, new_money):
        for asset, money in zip(self.assets, new_money):
            for ac, ratio in asset.class2ratio.items():
                self.aa[ac] = self.aa[ac][0], self.aa[ac][1] + ratio * money

    def solve(self):
        indices, derivatives = self.sorted_index_and_derivatives()

        x = np.zeros(len(indices))  # The return values (transformed).
        left_cash = self.cash

        for next_i in range(1, len(x)):
            target_derivative = derivatives[next_i]
            new_deltas = np.array([self.compute_delta(i, target_derivative)
                                   for i in indices[:next_i]])
            new_deltas = np.pad(new_deltas, (0, len(x) - next_i))
            new_cash = np.sum(new_deltas)

            if abs(new_cash) >= abs(left_cash):
                x += new_deltas * left_cash / new_cash
                left_cash = 0
                break

            x += new_deltas
            self.update_aa([new_deltas[i] for i in indices])
            left_cash = left_cash - new_cash

        # Handle the cash when left_cash > 0.
        if left_cash != 0:
            fake_derivative = derivatives[-1] + (
                derivatives[-1] - derivatives[0])
            new_deltas = np.array(
                [self.compute_delta(i, fake_derivative) for i in indices])
            new_cash = np.sum(new_deltas)
            x += new_deltas * left_cash / new_cash

        # Transform and return answer
        return [float(x[i]) for i in indices]


class Allocate(Analyzer):
    """Allocates any unallocated cash in the account to assets.

    If an account has any unallocated cash (aka what if) then this class
    allocates that cash to the assets in the account. The allocation is done
    with the goal of minimizing the relative ratio of actual allocation of
    asset classes to the desired allocation. Cash could be negative in which
    case money is removed from the assets.

    The allocation to assets is done via lakshmi.Portfolio.what_if function;
    and hence can be reset easily (by calling
    lakshmi.Portfolio.reset.what_ifs).
    """

    def __init__(self, account_name, blacklisted_assets=[], rebalance=False):
        """
        Args:
            account_name: The full name of the account to analyze.
            blacklisted_assets: A list of asset short names (strings) which
            will not be allocated any new cash from the account as a result
            of calling analyze.
            rebalance: If False, money is either only added (in case cash is
            positive) or removed (in case cash is negative) from the assets.
            If set, money is added and removed (as needed) from assets
            to minimize the relative difference from the desired asset
            allocation.
        """
        self.account_name = account_name
        self.blacklisted_assets = blacklisted_assets
        self.rebalance = rebalance

    def _apply_whatifs(self, portfolio, assets, deltas, saved_whatifs=None):
        """Apply whatifs given by deltas to assets in the portfolio."""
        table = Table(2, ['Asset', 'Delta'], ['str', 'delta_dollars'])
        if not saved_whatifs:
            saved_whatifs = [0] * len(assets)
        for asset, delta, saved in zip(assets, deltas, saved_whatifs):
            portfolio.what_if(self.account_name,
                              asset.short_name(),
                              delta)
            table.add_row([asset.short_name(), delta - saved])
        return table

    def analyze(self, portfolio):
        """Modifies portfolio by allocating any cash and returns the resulting
        changes.

        Args:
            portfolio: The portfolio on which to operate on. This portfolio is
            modified by applying what_ifs to the assets in the provided
            account.

        Returns:
            A table.Table of asset names and an delta for each of the asset.

        Throws:
            AssertionError: In case of
            - There is no cash to allocation and rebalance is False.
            - An asset class's desired allocation ratio is zero.
            - No assets are present in the Account after taking out the
            blacklisted assets.
            - Cash to withdraw is more than the total value of assets in the
            portfolio.
            - For some reason, we can't minimize the difference between
            relative error of actual vs desired allocation, given all the
            constraints.
        """
        account = portfolio.get_account(self.account_name)
        cash = account.available_cash()
        assert cash != 0 or self.rebalance, (
            f'No available cash to allocate in {self.account_name}.')
        assets = [x for x in account.assets() if x.short_name() not in
                  self.blacklisted_assets]
        assert len(assets) != 0, 'No assets to allocate cash to.'

        saved_whatifs = None
        if self.rebalance:
            saved_whatifs = []
            # Withdraw all cash and reallocate.
            for asset in assets:
                saved_whatifs += [asset.adjusted_value()]
                portfolio.what_if(self.account_name, asset.short_name(),
                                  -asset.adjusted_value())
            cash = account.available_cash()

        total = sum([asset.adjusted_value() for asset in assets])
        if abs(total + cash) < 1e-6:
            # Withdraw all cash and return.
            return self._apply_whatifs(
                portfolio, assets,
                [-asset.adjusted_value() for asset in assets])
        assert -cash < total, (
            f'Cash to withdraw ({format_money(-cash)}) is more than the total '
            f'available money in the account ({format_money(total)}).')

        # Map of leave asset classes -> (desired%, money)
        asset_allocation = {}
        for row in portfolio.asset_allocation(
                portfolio.asset_classes.leaves()).list():
            asset_allocation[row[0]] = row[2], row[3]

        for asset in assets:
            for ac in asset.class2ratio.keys():
                assert asset_allocation[ac][0] != 0, (
                    f'Desired ratio of asset class {ac} cannot be zero.')

        result = _Solver(
            asset_allocation, assets, cash, portfolio.total_value()).solve()
        return self._apply_whatifs(portfolio, assets, result, saved_whatifs)
