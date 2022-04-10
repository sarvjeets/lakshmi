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


def _dedup_assets(orig_assets):
    """Dedup assets which have exactly the same allocation accross asset
    classes (i.e. they are identical for allocation purposes). The dedups
    assets are stored in mapping, where key is index of deduped assets and
    values are the dups from orig_assets.
    """
    def has_same_allocation(asset1, asset2):
        for ac in asset1.class2ratio:
            if abs(asset1.class2ratio.get(ac, 0)
                   - asset2.class2ratio.get(ac, 0)) >= 1e-6:
                return False
        return True

    assets = []
    mapping = {}
    dups = []

    for i in range(len(orig_assets)):
        if i in dups:
            continue
        new_index = len(assets)
        mapping[new_index] = [i]
        assets.append(orig_assets[i])

        for j in range(i + 1, len(orig_assets)):
            if has_same_allocation(orig_assets[i], orig_assets[j]):
                mapping[new_index].append(j)
                dups.append(j)
    return assets, mapping


class _Solver:
    """Internal class to help allocate cash to portfolio (see next class).

    TODO: Add actual maths.
    """

    def __init__(self, aa, assets, cash, total):
        self.aa = aa
        self.total = total
        self.cash = cash
        self.assets, self.mapping = _dedup_assets(assets)

    def desired_ratio(self, asset_class):
        return self.aa[asset_class][0]

    def money(self, asset_class):
        return self.aa[asset_class][1]

    def update_aa(self, new_money):
        for asset, money in zip(self.assets, new_money):
            for ac, ratio in asset.class2ratio.items():
                self.aa[ac] = self.aa[ac][0], self.aa[ac][1] + ratio * money

    def derivative(self, i):
        # The actual derivative has (2/total_money) extra term, but as it is
        # common in all assets, we ignore it.
        sum = 0.0
        for j in self.assets[i].class2ratio.keys():
            rel_ratio = (self.money(j) / (self.desired_ratio(j) * self.total)
                         - 1)
            sum += rel_ratio * (self.assets[i].class2ratio[j]
                                / self.desired_ratio(j))
        return sum

    def expand_dup_assets(self, x):
        max_index = max(map(max, self.mapping.values()))
        ret_val = [None] * (max_index + 1)

        for i, dest_assets in self.mapping.items():
            for j in dest_assets:
                ret_val[j] = float(x[i] / len(dest_assets))

        return ret_val

    def compute_delta(self, source_assets, target_asset):
        a = []
        b = []
        n = target_asset
        alpha = self.derivative(n)

        for i in source_assets:
            equation_i = []
            for k in source_assets:
                coeff = 0.0
                for j in self.assets[k].class2ratio.keys():
                    coeff += ((self.assets[k].class2ratio[j]
                               / self.desired_ratio(j) ** 2)
                              * (self.assets[i].class2ratio.get(j, 0)
                                 - self.assets[n].class2ratio.get(j, 0)))
                equation_i.append(coeff)
            a.append(equation_i)
            const_i = self.total * alpha
            for j in self.assets[i].class2ratio.keys():
                const_i += ((self.assets[i].class2ratio[j]
                             / self.desired_ratio(j) ** 2)
                            * (self.desired_ratio(j) * self.total
                               - self.money(j)))
            if abs(const_i) <= 1e-10:
                b.append(0)
            else:
                b.append(const_i)

        solution = np.linalg.solve(a, b).tolist()
        x = np.zeros(len(self.assets))

        final_derivative = alpha
        for k in source_assets:
            x[k] = solution.pop(0)
            sum = 0.0
            for j in self.assets[n].class2ratio.keys():
                sum += (self.assets[n].class2ratio[j]
                        * self.assets[k].class2ratio.get(j, 0)
                        / self.desired_ratio(j) ** 2)
            final_derivative += sum * x[k] / self.total

        return x, final_derivative

    def allocate_all_cash(self, cash_to_allocate):
        a = []
        for i in range(len(self.assets)):
            equation_i = []
            for k in range(len(self.assets)):
                coeff = 0.0
                for j in self.assets[i].class2ratio.keys():
                    coeff += (self.assets[i].class2ratio[j]
                              * self.assets[k].class2ratio.get(j, 0)
                              / self.desired_ratio(j) ** 2)
                equation_i.append(coeff)
            a.append(equation_i)
        x = np.linalg.solve(a, [0.1 * self.total] * len(self.assets))
        x *= cash_to_allocate / np.sum(x)
        return x

    def solve(self):
        # Used to pick either the min or max gradient.
        best_gradient = np.argmin if self.cash > 0 else np.argmax

        equal_gradient_funds = set([best_gradient(
            [self.derivative(i) for i in range(len(self.assets))])])
        x = np.zeros(len(self.assets))
        left_cash = self.cash

        while len(equal_gradient_funds) != len(self.assets):
            derivatives = []
            deltas = []
            indices = []
            # Compute the min increase in gradient.
            for n in set(range(len(self.assets))) - equal_gradient_funds:
                delta, derivative = self.compute_delta(
                    equal_gradient_funds, n)
                derivatives.append(derivative)
                deltas.append(delta)
                indices.append(n)

            # Pick the highest or lowest derivative.
            best_fund_index = best_gradient(derivatives)
            best_delta = deltas[best_fund_index]
            new_cash = np.sum(best_delta)

            if abs(new_cash) >= abs(left_cash):
                # We have allocated more cash than what was left.
                x += best_delta * left_cash / new_cash
                left_cash = 0
                break

            equal_gradient_funds.add(indices[best_fund_index])
            x += best_delta
            self.update_aa(best_delta)
            left_cash = left_cash - new_cash

        # Handle any left over cash.
        if left_cash != 0:
            x += self.allocate_all_cash(left_cash)

        return self.expand_dup_assets(x)


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
