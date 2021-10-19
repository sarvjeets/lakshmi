"""Top level interfaces and definitions for Lakshmi."""

import yaml

import lakshmi.utils as utils
from lakshmi.assets import from_dict, to_dict
from lakshmi.table import Table


class Account:
    """Class representing an account (collection of assets)."""

    def __init__(self, name, account_type):
        """
        Args:
          name: Printable name for this account.
          account_type: Type of this account (string).
        """
        self._name = name
        self.account_type = account_type
        self._assets = {}
        self._cash = 0

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Name': self._name,
             'Account Type': self.account_type}
        if self._assets:
            d['Assets'] = [to_dict(asset) for asset in self._assets.values()]
        if self._cash != 0:
            d['Available Cash'] = self._cash
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d.

        This is reverse of to_dict.
        Args:
            d: A dictionary (usually the output of to_dict).

        Returns: A new Account object.

        Raises: AssertionError if d cannot be parsed correctly.
        """
        ret_obj = Account(d.pop('Name'), d.pop('Account Type'))
        for asset_dict in d.pop('Assets', []):
            ret_obj.add_asset(from_dict(asset_dict))
        ret_obj._cash = d.pop('Available Cash', 0)
        assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
        return ret_obj

    def string(self):
        """Returns a string representation of this object."""
        table = Table(2)
        table.add_row(['Name:', f'{self._name}'])
        table.add_row(['Type:', f'{self.account_type}'])
        total = sum([asset.adjusted_value()
                    for asset in self._assets.values()])
        table.add_row(['Total:', utils.format_money(total)])
        if self._cash:
            table.add_row(['Available Cash:',
                           utils.format_money_delta(self._cash)])
        return table.string(tablefmt='plain')

    def add_asset(self, asset, replace=False):
        """Add an asset to this Account.

        Args:
            asset: A lakshmi.assets.Asset object. The short_name of the
            asset must be unique in this account (unless replace is set
            to True).
            replace: If true, this asset will replace any other asset
            with the same short_name.

        Returns: The new account.

        Raises: AssertionError if another asset with the same short_name
        is present in the account (unless replace is True).
        """
        assert replace or asset.short_name() not in self._assets, (
            f'Attempting to add duplicate Asset: {asset.short_name()}')
        self._assets[asset.short_name()] = asset
        return self

    def assets(self):
        """Retuns all assets in this account."""
        return self._assets.values()

    def set_assets(self, assets):
        """Replaces all assets in this account with provided assets.

        Args:
            assets: A list of lakshmi.assets.Asset
        """
        self._assets = {}
        for asset in assets:
            self.add_asset(asset)

    def get_asset(self, short_name):
        """Returns an asset specified by short_name."""
        return self._assets[short_name]

    def remove_asset(self, short_name):
        """Removes the asset in this account specified by short_name."""
        del self._assets[short_name]

    def name(self):
        """Returns the name of this account."""
        return self._name

    def add_cash(self, delta):
        """Adds cash to this account."""
        self._cash += delta

    def available_cash(self):
        """Returns the available cash in this account."""
        return self._cash


class AssetClass:
    """This class represents (a tree of) Asset classes.

    Each asset class is specified by a name and can optionally have child
    asset classes. The child asset classes have a ratio (float) associated
    with them and the sum of all ratios must add to 1.0.

    Example of asset classes: Stocks, Bonds, US, International, Small Cap,
    Large Cap, etc.
    Some asset classes can have children asset classes. E.g.
    Stock -> US (60%) and International (40%).
    """

    def __init__(self, name):
        """Returns a new AssetClass object named name."""
        self.name = name
        self._children = []
        # Populated when _validate is called.
        self._leaves = None

    def children(self):
        """Returns a list of all the children of this asset class."""
        return self._children

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Name': self.name}
        if self._children:
            d['Children'] = [{'Ratio': ratio} | child.to_dict()
                             for child, ratio in self._children]
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d.

        This is reverse of to_dict.
        Args:
            d: A dictionary (usually the output of to_dict).

        Returns: A new AssetClass object.

        Raises: AssertionError if d cannot be parsed correctly.
        """
        ret_obj = AssetClass(d.pop('Name'))
        for child_dict in d.pop('Children', []):
            ret_obj.add_subclass(
                child_dict.pop('Ratio'),
                AssetClass.from_dict(child_dict))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj.validate()

    def copy(self):
        """Returns a copy of this AssetClass and its sub-classes."""
        ret_val = AssetClass(self.name)
        for child, ratio in self._children:
            ret_val.add_subclass(ratio, child.copy())
        return ret_val

    def add_subclass(self, ratio, asset_class):
        """Add a subclass (asset class) to this asset class.

        Args:
            ratio: The ratio of this asset class.
            asset_class: An AssetClass object representing the child class.
        """
        self._children.append((asset_class, ratio))
        # leaves is not upto date now, need validation again.
        self._leaves = None
        return self

    def _validate(self):
        """Internal helper method to validate this asset class.

        Returns: A tuple (leaf names, class names) for the subtree containing
        set of all the leaf asset class names and list of all (including
        non-leaf) asset classes.

        Raises: AssertionError If ratio is not a valid float in [0, 1] or if
        the sum of ratio of all the sub-classes doesn't add up to 1.0.
        """
        if not self._children:
            self._leaves = {self.name}
            return self._leaves, [self.name]

        self._leaves = set()
        class_names = [self.name]
        total = 0.0
        for asset_class, ratio in self._children:
            assert ratio >= 0.0 and ratio <= 1.0, (
                f'Bad ratio provided to Asset Class ({ratio})')
            total += ratio
            temp_leafs, temp_classes = asset_class._validate()
            self._leaves.update(temp_leafs)
            class_names += temp_classes

        # Check if all percentages add up to 100%
        assert abs(total - 1) < 1e-6, (
            f'Sum of sub-classes is not 100% (actual: {total * 100}%)')

        return self._leaves, class_names

    def validate(self):
        """Validates if this asset class tree has any errors.

        This function checks the ratios and also if the asset class tree has
        any duplicate asset class names. It also sets an internal field which
        is used by few other methods in this class. Those methods will raise
        an exception if they are called without calling validate.

        Returns: self

        Raises: AssertionError if there are any duplicate asset classes in the
        tree.
        """
        unused_leaves, all_class_names = self._validate()
        duplicates = set([x for x in all_class_names
                          if all_class_names.count(x) > 1])

        assert not duplicates, f'Found duplicate Asset class(es): {duplicates}'
        return self

    def _check(self):
        """Internal method to check if validate has been called."""
        assert self._leaves, (
            'Need to validate AssetAllocation before using it.')

    def find_asset_class(self, asset_class_name):
        """Returns asset_class_name object and its desired ratio.

        validate() must be called before calling this method.
        This methods searches for an asset class object with name
        asset_class_name in the current asset tree and returns the found
        object and the effective _absolute_ ratio of that asset class as
        a tuple. If the asset_class_name is not found, this method returns
        None. For example, if the asset class tree is:
        All -> Stocks 60%, Bonds 40%
        Stocks -> US 60%, Intl 40%
        find_asset_class('US') will return asset class representing the 'US'
        node and 0.36 as ratio (= 0.6 * 0.6).

        Args:
            asset_class_name: A string representing the name to be searched.

        Returns: (Found asset class object, absolute ratio (float)) or None
        if the asset_class_name is not found in this asset class tree.

        Raises: AssertionError if validate is not callled before calling this
        method.
        """
        self._check()

        if self.name == asset_class_name:
            return self, 1.0

        for asset_class, ratio in self._children:
            ret_value = asset_class.find_asset_class(asset_class_name)
            if ret_value:
                return ret_value[0], ret_value[1] * ratio

        return None

    def leaves(self):
        """Returns all leaf asset class names.

        validate() must be called before calling this method.

        Returns: A list of leaf asset class names.

        Raises: AssertionError if validate is not callled before calling this
        method.
        """
        self._check()
        return self._leaves

    def value_mapped(self, money_allocation):
        """Returns how much money is mapped to this Asset Class.

        validate() must be called before calling this method.
        Given a money allocation, this class return the amount of money mapped
        to this asset class or its childen.

        Ars:
          money_allocation: A map of leaf_class_names (string) -> money
          (float).

        Returns: Total amount of money mapped to this asset class.

        Raises: AssertionError if validate is not callled before calling this
        method.
        """
        self._check()
        return sum([value for name, value in money_allocation.items()
                    if name in self._leaves])

    class Allocation:
        """This class is a convenience class to represent the return value of
        return_allocation method. This class represents a partcular node of
        AssetClass + its direct children and also the money allocated to the
        asset class and its direct children. It is meant to be used as a
        data-only class.
        """
        class Children:
            """Class representing a child of Allocation class. This class is
            meant to be used as a data-only class.
            """
            def __init__(self, name, actual_allocation, desired_allocation,
                         value, value_difference):
                """
                Args:
                    name: Name of the child asset class.
                    actual_allocation: Actual allocation (ratio, float).
                    desired_allocation: Desired asset allocation (ratio,
                    float).
                    value: The absolute amount of money allocated to this
                    child.
                    value_difference: The difference between desired and
                    actual allocation.
                """
                self.name = name
                self.actual_allocation = actual_allocation
                self.desired_allocation = desired_allocation
                self.value = value
                self.value_difference = value_difference

        def __init__(self, name, value):
            """
            Args:
                name: Name of this asset class.
                value: The absolute amount of money allocated to this asset
                class.
            """
            self.name = name
            self.value = value
            self.children = []

        def add_child(self, name, actual, desired):
            """Add a child asset to this asset class.

            Args:
                name: Name of the child asset class.
                actual: The actual amount of money allocated to this child.
                desired: The desired alloction of money for this child.
            """
            self.children.append(
                self.Children(name, actual, desired, actual * self.value,
                              (desired - actual) * self.value))

    def return_allocation(self, money_allocation, levels=-1):
        """Returns actual and desired allocation based on how money is allocated.

        Args:
          money_allocation: A map of leaf_class_name -> money.
          levels: How many levels of child allocation to return (-1 = all).

        Returns: A list of Allocation objects (for itself and any child classes
        based on the levels flag).
        """
        value = self.value_mapped(money_allocation)
        actual_alloc = self.Allocation(self.name, value)

        if value == 0:
            return [actual_alloc]

        for asset_class, desired_ratio in self._children:
            actual_ratio = asset_class.value_mapped(money_allocation) / value
            actual_alloc.add_child(
                asset_class.name,
                actual_ratio,
                desired_ratio)

        ret_val = [actual_alloc]

        if levels == 0:
            return ret_val

        if levels > 0:
            levels -= 1

        for asset_class, unused_ratio in self._children:
            ret_val += asset_class.return_allocation(money_allocation, levels)

        return ret_val


class Portfolio:
    """Top-level class representing a portfolio.

    A portfolio consists of multiple accounts (Account objects). This
    class provides helper methods to add/delete accounts etc. This class
    also provides methods for portfolio level operations.
    """
    def __init__(self, asset_classes):
        """
        Args:
            asset_classes: An AssetClass object representing the desired asset
            allocation.
        """
        self._accounts = {}
        self.asset_classes = asset_classes.validate()
        self._leaf_asset_classes = asset_classes.leaves()

    def save(self, filename):
        """Save this portfolio to a file."""
        with open(filename, 'w') as f:
            yaml.dump(self.to_dict(), f, sort_keys=False)

    @classmethod
    def load(cls, filename):
        """Loads and returns portfolio from file."""
        with open(filename) as f:
            d = yaml.load(f.read(), Loader=yaml.SafeLoader)
        return Portfolio.from_dict(d)

    def to_dict(self):
        """Returns a dictionary representation of this portfolio."""
        d = {'Asset Classes': self.asset_classes.to_dict()}
        if self._accounts:
            d['Accounts'] = [account.to_dict()
                             for account in self._accounts.values()]
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a portfolio represented by dict d (reverse of to_dict)."""
        ret_obj = Portfolio(AssetClass.from_dict(d.pop('Asset Classes')))
        for account_dict in d.pop('Accounts', []):
            ret_obj.add_account(Account.from_dict(account_dict))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def add_account(self, account, replace=False):
        """Add an account to this portfolio.

        This method adds a new account to this portfolio. The account
        name must be unique unless replace is set to True.

        Returns: self object with account added.

        Raises:
            AssertionError: If any of the assets are mapped to asset classes
            that doesn't match the asset classes given the asset allocation
            provided when creating this class.
            AssertError: If another account with the same exists in the
            portfolio and replace=False.
        """
        for asset in account.assets():
            for asset_class in asset.class2ratio.keys():
                assert asset_class in self._leaf_asset_classes, (
                    f'Unknown or non-leaf asset class: {asset_class}')

        assert replace or account.name() not in self._accounts, (
            f'Attempting to add duplicate account: {account.name()}')

        self._accounts[account.name()] = account
        return self

    def remove_account(self, account_name):
        """Delete account specifed by account_name."""
        del self._accounts[account_name]

    def accounts(self):
        """Returns a list (dict_values) of accounts."""
        return self._accounts.values()

    def get_account(self, name):
        """Return Account object represented by name."""
        return self._accounts[name]

    def get_account_name_by_substr(self, account_str):
        """Returns account name whose name partially matches account_str.

        Args:
            account_str: String used for sub-string matching (case-sensitive).

        Raises: AssertionError if more than one or none of the accounts match
        the account_str.
        """

        matched_accounts = list(
            filter(lambda x: x.count(account_str),
                   [account.name() for account in self.accounts()]))
        if len(matched_accounts) == 0:
            raise AssertionError(f'{account_str} does not match any account '
                                 'in the portfolio')
        if len(matched_accounts) > 1:
            raise AssertionError(f'{account_str} matches more than one '
                                 'account in the portfolio')
        return matched_accounts[0]

    def get_asset_name_by_substr(self, account_str='', asset_str=''):
        """Returns asset names given a sub-string for account and asset.

        Args:
            account_str: String used for sub-string matching with account
            names (case-sensitive).
            asset_str: String used for sub-string matching with asset
            names or asset short names (case-sensitive).

        Returns: A tuple account_name, asset_name where account name
        partially matches account_str and asset name partially matches
        asset_str or asset short name == asset_str

        Raises: AssertionError if none or more than one asset matches the
        sub-strings."""
        matched_assets = list(filter(
            lambda x: x[0].count(account_str) and (
                x[1].count(asset_str) or x[2] == asset_str),
            [(account.name(), asset.name(), asset.short_name())
             for account in self.accounts()
             for asset in account.assets()]))
        if len(matched_assets) < 1:
            raise AssertionError(
                'Provided asset and account strings match none '
                'of the assets.')
        if len(matched_assets) > 1:
            raise AssertionError(
                'Provided asset and account strings match more '
                'than one assets.')
        return matched_assets[0][0], matched_assets[0][2]

    def what_if(self, account_name, asset_name, delta):
        """Changes value of an asset by delta.

        This method runs a whatif scenario if asset_name in account_name
        is changed by delta. The account cash balance is changed with
        -delta to balance the transaction.

        Args:
            account_name: String representing the account name.
            asset_name: String representing the asset name.
            delta: A positive or negative delta for money.
        """
        account = self.get_account(account_name)
        asset = account.get_asset(asset_name)
        asset.what_if(delta)
        # We take the money out of account.
        account.add_cash(-delta)

    def what_if_add_cash(self, account_name, cash_delta):
        """Changes available cash balance of an account by delta."""
        self.get_account(account_name).add_cash(cash_delta)

    def get_what_ifs(self):
        """Returns all what_ifs set by previous methods.

        Returns: A tuple of two table.Table representing
        account whatifs and asset what ifs respectively. The first
        table has columns Account and Cash; and the second table has
        columns Account, Asset and Delta (representing money).
        """
        account_whatifs = Table(
            2,
            headers=['Account', 'Cash'],
            coltypes=['str', 'delta_dollars'])
        asset_whatifs = Table(
            3,
            headers=['Account', 'Asset', 'Delta'],
            coltypes=['str', 'str', 'delta_dollars'])

        for account in self.accounts():
            if account.available_cash() != 0.0:
                account_whatifs.add_row(
                    [account.name(), account.available_cash()])
            for asset in account.assets():
                delta = asset.get_what_if()
                if delta != 0.0:
                    asset_whatifs.add_row(
                        [account.name(), asset.name(), delta])

        return account_whatifs, asset_whatifs

    def reset_what_ifs(self):
        """Reset all previously set what ifs in this portfolio."""
        for account in self.accounts():
            account.add_cash(-account.available_cash())
            for asset in account.assets():
                asset.what_if(-asset.get_what_if())

    def total_value(self):
        """Returns total value of the portfolio."""
        total = 0.0
        for account in self.accounts():
            total += account.available_cash()
            for asset in account.assets():
                total += asset.adjusted_value()
        return total

    # TODO: Renmame this to list_assets for consistency.
    def assets(self, short_name=False, quantity=False):
        """Returns all the assets.

        Args:
            short_name: If set, returns the short name of the asset as well.
            quantity: If set, returns the shares/quantity of the asset for
            the assets that support it.

        Returns: A table.Table object representing all the assets.
        The columns correspond to Account name, short name (optional),
        quantity (optional), asset name and value.
        """
        table = Table(
            3 + short_name + quantity,
            headers=(['Account']
                     + (['Name'] if short_name else [])
                     + (['Quantity'] if quantity else [])
                     + ['Asset', 'Value']),
            coltypes=(['str']
                      + (['str'] if short_name else [])
                      + (['float'] if quantity else [])
                      + ['str', 'dollars']))
        for account in self.accounts():
            for asset in account.assets():
                row = ([account.name()]
                       + ([f'{asset.short_name()}'] if short_name else [])
                       + [asset.name(), asset.adjusted_value()])
                if quantity:
                    row.insert(1 + short_name, asset.shares()
                               if hasattr(asset, 'shares') else None)
                table.add_row(row)
        return table

    def list_lots(self):
        """Returns all the tax lots in the portfolio.

        Returns: A table.Table object representing tax lots
        for assets that support it. The columns of the returned table are
        short name (of asset), date of lot, cost basis of lot, gain (+ve or
        -ve) and percentage gain.
        """
        table = Table(
            5,
            headers=['Short Name', 'Date', 'Cost', 'Gain', 'Gain%'],
            coltypes=['str', 'str', 'dollars', 'delta_dollars', 'percentage'])
        for account in self.accounts():
            for asset in account.assets():
                if hasattr(asset, 'list_lots'):
                    lots = asset.list_lots()
                    assert (
                        lots.headers()
                        == ['Date', 'Quantity', 'Cost', 'Gain', 'Gain%'])
                    for lot in lots.list():
                        table.add_row([asset.short_name()] + lot[:1] + lot[2:])
        return table

    def asset_location(self):
        """Returns asset location of this portfolio.

        Returns: A table.Table object representing the asset location.
        The columns of the table correspond to Asset class name, account type,
        percentage allocation to account type and total monetary value.
        """
        class2type = {}  # Mapping of asset class -> account type -> money
        for account in self.accounts():
            for asset in account.assets():
                for name, ratio in asset.class2ratio.items():
                    if name not in class2type:
                        class2type[name] = {}
                    class2type[name][account.account_type] = (
                        class2type[name].get(account.account_type, 0)
                        + ratio * asset.adjusted_value())

        table = Table(
            4,
            headers=['Asset Class', 'Account Type', 'Percentage', 'Value'],
            coltypes=['str', 'str', 'percentage', 'dollars'])

        for asset_class, type2value in class2type.items():
            first = True
            total = sum(type2value.values())
            if abs(total) < 1e-6:
                continue
            for account_type, value in sorted(
                    type2value.items(),
                    key=lambda x: x[1],
                    reverse=True):
                table.add_row([asset_class if first else '', account_type,
                               value / total, value])
                first = False
        return table

    def _get_asset_class_to_value(self):
        """Returns asset class name -> money allocated to it."""
        asset_class_to_value = {}

        for account in self.accounts():
            for asset in account.assets():
                for name, ratio in asset.class2ratio.items():
                    asset_class_to_value[name] = asset_class_to_value.get(
                        name, 0) + ratio * asset.adjusted_value()

        return asset_class_to_value

    def asset_allocation_tree(self, levels=-1):
        """Returns asset allocation in long vertical tree format.

        Args:
            levels: The max depth of asset allocation tree (-1 = all levels).

        Returns: table.Table object representing the asset allocation. The
        table has multiple sections separated by empty row, each corresponding
        to an asset class and it's children asset class. The first row in a
        section is the asset class name followed by ":". The remaining rows
        correspond to the direct children of the asset class. For these
        rows the columns correspond to asset class name, actual percentage of
        money allocated to it, the desired percentage of money allocated, and
        the actual money allocated to it.
        """
        table = Table(4,
                      headers=['Class', 'Actual%', 'Desired%', 'Value'],
                      coltypes=['str', 'percentage', 'percentage', 'dollars'])
        first_row = True
        for alloc in self.asset_classes.return_allocation(
                self._get_asset_class_to_value(), levels):
            if not alloc.children:
                continue

            if not first_row:
                table.add_row([' '])
            first_row = False
            table.add_row([f'{alloc.name}:'])
            for child in alloc.children:
                table.add_row([child.name,
                              child.actual_allocation,
                              child.desired_allocation,
                              child.value])
        return table

    def asset_allocation(self, asset_class_list):
        """Returns asset allocation across the asset classes provided.

        This method returns the asset allocation, but only across the asset
        classes provided via asset_class_list. This requires that the asset
        class list provided represents a "cut" of the asset class tree. What
        it means is that the asset list should cover the asset tree completely.
        None of the asset classes should be a descendent or ancestor of another
        and the sum of actual allocation across the asset class list must add
        up to 100%.

        Args:
            asset_class_list: A list of strings representing the asset classes
            across which the asset allocation should be returned.

        Returns: A table.Table object representing the asset allocation. The
        columns represent asset class name, actual percentage allocation to
        the asset class, the desired percentage allocation of money to the
        asset class, the absolute money allocated to it and difference from
        the desired amount of money allocated.

        Raises: AssertionError is the asset_class_list is not a proper
        "cut" of the asset class tree.
        """
        flat_asset_class = AssetClass('Root')
        for asset_class in asset_class_list:
            found = self.asset_classes.find_asset_class(asset_class)
            assert found, f'Could not find {asset_class}'
            flat_asset_class.add_subclass(found[1], found[0])

        try:
            flat_asset_class.validate()
        except AssertionError:
            raise AssertionError(
                'AssetAllocation called with overlapping '
                'Asset Classes or Asset Classes which does not cover the '
                'full tree.') from None

        alloc = flat_asset_class.return_allocation(
            self._get_asset_class_to_value(), 0)[0]
        table = Table(
            5,
            headers=['Class', 'Actual%', 'Desired%', 'Value', 'Difference'],
            coltypes=['str', 'percentage', 'percentage', 'dollars',
                      'delta_dollars'])
        for child in alloc.children:
            table.add_row([child.name, child.actual_allocation,
                          child.desired_allocation, child.value,
                          child.value_difference])
        return table

    def asset_allocation_compact(self):
        """Returns asset allocation in long horizontal format.

        This method is similar to asset_allocaton_tree method in terms of
        informaiton returned, but this method returns the asset allocation
        in horizontal format.

        Returns: A table.Table object representing the portfolio's asset
        allocation. Each row corresponds to a path in the asset allocation
        tree. The columns are grouped into groups of three for each node
        in the tree (except the final two columns). The three columns for
        each node correspond to the asset class name, actual percentage
        of assets mapped to the asset class, and the desired percentage
        of assets. The final two columns are corresponding to the leaf
        nodes of asset allocation: They contain the actual value of assets
        mapped to the leaf node, and the difference from the desired
        value of assets mapped to the leaf node, respectively.
        """
        def find_index(class_name, ret_list):
            # We assume ret_list has atleast one entry.
            names_list = [row[-3] for row in ret_list]
            return names_list.index(class_name)

        ret_list = []
        for alloc in self.asset_classes.return_allocation(
                self._get_asset_class_to_value()):
            if not alloc.children:
                continue

            if not ret_list:
                for child in alloc.children:
                    ret_list.append([child.name,
                                     child.actual_allocation,
                                     child.desired_allocation])
            else:  # Parent is already in ret_list
                index = find_index(alloc.name, ret_list)
                # We know that here is atleast one child.
                for i in range(len(alloc.children) - 1):
                    # Make room for rest of the children by inserting empty
                    # extra rows of the same size as the parent's row
                    ret_list.insert(index + 1, [None] * len(ret_list[index]))
                for i in range(len(alloc.children)):
                    ret_list[index + i].extend(
                        [alloc.children[i].name,
                         alloc.children[i].actual_allocation,
                         alloc.children[i].desired_allocation])

        # Return early if there is no AA.
        if not ret_list:
            return Table(0)

        # By this time ret_list has all the AA tree.
        # Add Leaf node AA at the end.
        cols = max(map(len, ret_list))
        leaf_aa = self.asset_allocation(self.asset_classes.leaves())
        for leaf_row in leaf_aa.list():  # Format: Class, A%, D%, Value, Diff
            ret_list_row = ret_list[find_index(leaf_row[0], ret_list)]
            ret_list_row.extend([None] * (cols - len(ret_list_row)))
            ret_list_row.extend(leaf_row[1:])

        # All done, now build the table.
        t = Table(cols + 4,
                  headers=['Class', 'A%', 'D%'] * int(cols / 3)
                  + leaf_aa.headers()[1:],
                  coltypes=['str', 'percentage', 'percentage'] * int(cols / 3)
                  + ['percentage', 'percentage', 'dollars', 'delta_dollars'])
        t.set_rows(ret_list)
        return t
