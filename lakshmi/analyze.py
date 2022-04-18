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
    """Internal class to help allocate cash to portfolio (helper class for the
    next class).

    TODO: Fix this documentation.

    I tried using scipy optimize instead of this custom solver and it was
    extremely flaky for this purposes (even after scaling/conditioning the
    inputs well). So finally, I came up these heuristics which work (mostly).
    This class can be further optimized/fixed, but for now it serves its
    purpose.

    Notation:
    - f_i: Money in fund i orginally.
    - x_i: New money to be added to fund i (what we are solving for).
    - A_j: Money in asset class j.
    - C_j: Money in asset class j before adding new money (implementd as
    self.money)
    - d_j: Desired ratio of asset class j (implemented as self.desired_ratio).
    - a_{ij}: Ratio of fund i in asset class j (implemented as
    self.allocation).

    So,
    A_j = \\sum_i a_{ij} (f_i + x_i)
    \\sum_j A_j = T (a constant, given by self.total)

    Error E = \\sum_j (A_j/(d_j T) - 1)^2

    Derivative wrt a fund i (implemented as self.derivative)
    dE/dx_i = (2/T) \\sum_j (a_{ij} / d_j) (A_j/(d_j T) - 1)
    Rate of change of above derivative wrt fund k:
    d^2E/{dx_i dx_k} = (2/T^2) \\sum_j (a_{ij} a_{kj} / d^2_j)

    The algorithm (somewhat of a heuristic right now, althrough I suspect that
    it is correct, but I haven't formally proved it):
    0. Without lost of generality, assume cash to be allocated is positive (
    the other way round just replaces min with max in the following algo). We
    also dedup same funds so that the equations in Step 2 has a unique
    solution.
    1. Start by the lowest derivative fund.
    2. Add money to fund to match a target fund. Pick the next target
    fund based on whichever target fund leads to lowest derivative.
    3. Now we have two funds with same derivatives, keep repeating step 2
    until all funds have same derivatives.
    4. If we run out of cash to allocate before all funds have same derivative,
    exit early.
    5. If we still have money after all funds have same derivative, add extra
    money to all funds while keeping their derivatives the same.

    For step 2, we solve the following linear equations:
    k is summing over funds with same derivatives. n is target fund to which
    we are not adding money (aka x_n = 0).

    For each i:
    dE/dx_i + \\sum_{k != i} x_k d^2E/{dx_i dx_k} =
                 dE/dx_n + \\sum_k x_k d^2E/{dx_i dx_k}
    (This equation is solved in self.compute_delta).

    self.allocate_all_cash solves:
    dE/dx_i + \\sum_{k != i} x_k d^2E/{dx_i dx_k} =
                 dE/dx_i (without x_i allocated to it) + 0.1
    which simplifies to:
    for each i:
    \\sum_k (x_k \\sum_j a{ij} a_{kj} / d^2_j = 0.1T
    """

    def __init__(self, aa, assets, cash, total):
        """Creates a new object.

        Args:
            aa: Map of asset class name to a tuple of desired_ratio and
            money allocated to it.
            assets: List of lakshmi.Assets to which to allocate the money to.
            cash: The cash to be allocated.
            total: The total value of the portfolio (T in equation above).
        """
        self.aa = aa
        self.total = total
        self.cash = cash
        self.assets = assets
        # Used to pick either the min or max gradient.
        self.best_gradient_fn = np.argmin if cash > 0 else np.argmax
        self.adjusted_values = [asset.adjusted_value() for asset in assets]

    def desired_ratio(self, asset_class):
        """Helper function to give desired ratio of an asset class."""
        return self.aa[asset_class][0]

    def money(self, asset_class):
        """Helper function to give money allocated to an asset class."""
        return self.aa[asset_class][1]

    def asset_classes(self):
        """Returns list of asset classes."""
        return self.aa.keys()

    def allocation(self, i, j):
        """Returns allocation of fund i in asset class j."""
        return self.assets[i].class2ratio.get(j, 0.0)

    def update_aa(self, new_money):
        """Updates self.aa with new_money.

        Args:
            new_money: A list of deltas to be which new_money[i] is for
            self.assets[i].
        """
        for asset, money in zip(self.assets, new_money):
            for ac, ratio in asset.class2ratio.items():
                self.aa[ac] = self.aa[ac][0], self.aa[ac][1] + ratio * money

    def derivative(self, i):
        """Computes dE/dx_i. The actual derivative has (2/T) extra
        term, but as it is common in all assets, we ignore it (the rest of the
        computations in equations are done correctly to account for a missing
        2/T factor).
        """
        sum = 0.0
        for j in self.asset_classes():
            rel_ratio = (self.money(j) / (self.desired_ratio(j) * self.total)
                         - 1)
            sum += rel_ratio * (self.allocation(i, j) / self.desired_ratio(j))
        return sum

    def compute_delta(self, source_assets, target_asset):
        """Heart of this solver. This computes deltas (x) on the source_
        assets, so that the derivative of the error function wrt source_assets
        is equal to the target_asset.

        Args:
            source_assets: A set of indices referring to self.assets
            representing assets on which to compute deltas on.
            target_asset: An index referring to an asset in self.assets. The
            delta is computed for source_assets to make their error
            derivative equal to the target_asset.

        Returns: A tuple of computed deltas and the final derivative. The
        derivative of target asset can change based on the deltas computed.
        """
        a = []
        b = []
        n = target_asset
        alpha = self.derivative(n)

        for i in source_assets:
            equation_i = []
            for k in source_assets:
                coeff = 0.0
                for j in self.asset_classes():
                    coeff += (
                        (self.allocation(k, j) / self.desired_ratio(j) ** 2)
                        * (self.allocation(i, j) - self.allocation(n, j)))
                equation_i.append(coeff)
            a.append(equation_i)
            const_i = self.total * alpha
            for j in self.asset_classes():
                const_i += (
                    (self.allocation(i, j) / self.desired_ratio(j) ** 2)
                    * (self.desired_ratio(j) * self.total - self.money(j)))
            b.append(const_i)

        solution = np.linalg.lstsq(a, b, rcond=None)[0].tolist()
        x = np.zeros(len(self.assets))

        final_derivative = alpha
        for k in source_assets:
            x[k] = solution.pop(0)
            sum = 0.0
            for j in self.asset_classes():
                sum += (self.allocation(n, j) * self.allocation(k, j)
                        / self.desired_ratio(j) ** 2)
            final_derivative += sum * x[k] / self.total

        return x, final_derivative

    def allocate_all_cash(self, cash_to_allocate, equal_gradient_funds):
        """Allocates all the remaining cash. This function assumes that
        all the derivatives of the error function wrt assets are the same.
        Then it solves for extra deltas in each asset that will increase
        the derivative by 0.1 (arbitrary number). It then re-scales this
        number to make sure that the new deltas equal to cash_to_allocate.
        The exact computation is listed in the class level comment.

        Args:
            cash_to_allocate: The cash to allocate.

        Returns: deltas (x), one for each self.asset that sums up to
        cash_to_allocate and ensures the final derivatives of error function
        wrt all assets are equal.
        """
        a = []
        for i in equal_gradient_funds:
            equation_i = []
            for k in equal_gradient_funds:
                coeff = 0.0
                for j in self.asset_classes():
                    coeff += (self.allocation(i, j) * self.allocation(k, j)
                              / self.desired_ratio(j) ** 2)
                equation_i.append(coeff)
            a.append(equation_i)
        x = np.linalg.lstsq(a, [0.1 * self.total] * len(equal_gradient_funds),
                            rcond=None)[0]
        x *= cash_to_allocate / np.sum(x)

        ret_val = [0] * len(self.assets)
        for i, j in zip(equal_gradient_funds,
                        range(len(equal_gradient_funds))):
            ret_val[i] = x[j]

        return ret_val

    def bound_at_zero(self, x, deltas, equal_gradient_funds, zeroed_funds):
        """Ensure that none of the solution exceeds the available money in the
        fund.

        TODO: Add documentation.
        """
        if self.cash > 0:
            # in this case, we don't have to worry about bounding the money,
            # as we only add money to funds and never remove it.
            return None

        new_deltas = [0] * len(deltas)
        adjusted = False

        for i in equal_gradient_funds:
            money_removed = -(x[i] + deltas[i])
            if money_removed > self.adjusted_values[i]:
                # Withdrew too much money.
                new_deltas[i] = -(self.adjusted_values[i] + x[i])
                zeroed_funds.add(i)
                adjusted = True
            else:
                new_deltas[i] = 0

        equal_gradient_funds -= zeroed_funds

        # Handle the case when we zero out all equal_gradient_funds.

        # TODO: Fix me! AA needs to be updated.

        return new_deltas if adjusted else None

    def solve(self):
        """The main method. This method implements the algorithm listed in the
        class comment.
        """
        # Pick the lowest error gradient asset.
        equal_gradient_funds = set([self.best_gradient_fn(
            [self.derivative(i) for i in range(len(self.assets))])])
        zeroed_funds = set({})
        x = np.zeros(len(self.assets))
        left_cash = self.cash

        # Keep equalizing and adding an asset to equal_gradient_funds.
        while ((len(equal_gradient_funds)
                + len(zeroed_funds) != len(self.assets))
               and abs(left_cash) > 1e-6):
            if len(equal_gradient_funds) == 0:
                equal_gradient_funds.add(self.best_gradient_fn(
                    [self.derivative(i) for i in range(len(self.assets)) if
                     i not in zeroed_funds]))

            derivatives = []
            deltas = []
            indices = []
            # Compute the min increase in gradient among the remaining funds.
            for n in set(range(len(self.assets))) - equal_gradient_funds:
                delta, derivative = self.compute_delta(
                    equal_gradient_funds, n)
                derivatives.append(derivative)
                deltas.append(delta)
                indices.append(n)

            # Pick the highest or lowest derivative.
            best_fund_index = self.best_gradient_fn(derivatives)
            best_delta = deltas[best_fund_index]
            new_cash = np.sum(best_delta)

            if abs(new_cash) >= abs(left_cash):
                # We have allocated more cash than what was left.
                best_delta = best_delta * left_cash / new_cash
                new_cash = left_cash

            new_delta = self.bound_at_zero(
                x, best_delta, equal_gradient_funds, zeroed_funds)
            if new_delta:
                best_delta = new_delta
            x += best_delta
            self.update_aa(best_delta)
            left_cash -= np.sum(best_delta)
            if not new_delta:  # No zeroed funds.
                equal_gradient_funds.add(indices[best_fund_index])

        # Handle any left over cash.
        while abs(left_cash) > 1e-6:
            delta = self.allocate_all_cash(left_cash, equal_gradient_funds)
            new_delta = self.bound_at_zero(x, delta, equal_gradient_funds,
                                           zeroed_funds)
            if new_delta:
                delta = new_delta
            x += delta
            self.update_aa(delta)
            left_cash -= np.sum(delta)

        return x


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
