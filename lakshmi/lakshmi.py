"""Top level interfaces and definitions for Lakshmi."""

import yaml

import lakshmi.utils as utils
from lakshmi.assets import from_dict, to_dict
from lakshmi.table import Table


class Account:
    """Class representing an account."""

    def __init__(self, name, account_type):
        """
        Arguments:
          name: Printable name for this account.
          account_type: Type of this account.
        """
        self._name = name
        self.account_type = account_type
        self._assets = {}
        self._cash = 0

    def to_dict(self):
        d = {'Name': self._name,
             'Account Type': self.account_type}
        if self._assets:
            d['Assets'] = [to_dict(asset) for asset in self._assets.values()]
        if self._cash != 0:
            d['Available Cash'] = self._cash
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = Account(d.pop('Name'), d.pop('Account Type'))
        for asset_dict in d.pop('Assets', []):
            ret_obj.add_asset(from_dict(asset_dict))
        ret_obj._cash = d.pop('Available Cash', 0)
        assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
        return ret_obj

    def string(self):
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
        assert replace or asset.short_name() not in self._assets, (
            f'Attempting to add duplicate Asset: {asset.short_name()}')
        self._assets[asset.short_name()] = asset
        return self

    def assets(self):
        return self._assets.values()

    def set_assets(self, assets):
        self._assets = {}
        for asset in assets:
            self.add_asset(asset)

    def get_asset(self, short_name):
        return self._assets[short_name]

    def remove_asset(self, short_name):
        del self._assets[short_name]

    def name(self):
        return self._name

    def add_cash(self, delta):
        self._cash += delta

    def available_cash(self):
        return self._cash


class AssetClass:
    """(Tree of) Asset classes."""

    def __init__(self, name):
        self.name = name
        self._children = []
        # Populated when _validate is called.
        self._leaves = None

    def children(self):
        return self._children

    def to_dict(self):
        d = {'Name': self.name}
        if self._children:
            d['Children'] = [{'Ratio': ratio} | child.to_dict()
                             for child, ratio in self._children]
        return d

    @classmethod
    def from_dict(cls, d):
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
        self._children.append((asset_class, ratio))
        # leaves is not upto date now, need validation again.
        self._leaves = None
        return self

    def _validate(self):
        """Returns a tuple (leaf names, class names) for the subtree."""
        # Check if all percentages add up to 100%
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

        assert abs(total - 1) < 1e-6, (
            f'Sum of sub-classes is not 100% (actual: {total * 100}%)')

        return self._leaves, class_names

    def validate(self):
        unused_leaves, all_class_names = self._validate()
        duplicates = set([x for x in all_class_names
                          if all_class_names.count(x) > 1])

        assert not duplicates, f'Found duplicate Asset class(es): {duplicates}'
        return self

    def _check(self):
        assert self._leaves, (
            'Need to validate AssetAllocation before using it.')

    def find_asset_class(self, asset_class_name):
        """Returns a tuple of object representing asset_class_name and its
        desired ratio.

        Returns None if asset_class_name is not found."""
        self._check()

        if self.name == asset_class_name:
            return self, 1.0

        for asset_class, ratio in self._children:
            ret_value = asset_class.find_asset_class(asset_class_name)
            if ret_value:
                return ret_value[0], ret_value[1] * ratio

        return None

    def leaves(self):
        self._check()
        return self._leaves

    def value_mapped(self, money_allocation):
        """Returns how much money is mapped to this Asset Class or its
        children.

        Arguments:
          money_allocation: A map of leaf_class_name -> money.
        """
        self._check()
        return sum([value for name, value in money_allocation.items()
                    if name in self._leaves])

    class Allocation:
        class Children:
            def __init__(self, name, actual_allocation, desired_allocation,
                         value, value_difference):
                self.name = name
                self.actual_allocation = actual_allocation
                self.desired_allocation = desired_allocation
                self.value = value
                self.value_difference = value_difference

        def __init__(self, name, value):
            self.name = name
            self.value = value
            self.children = []

        def add_child(self, name, actual, desired):
            self.children.append(
                self.Children(name, actual, desired, actual * self.value,
                              (desired - actual) * self.value))

    def return_allocation(self, money_allocation, levels=-1):
        """Returns actual and desired allocation based on how money is allocated.

        Arguments:
          money_allocation: A map of leaf_class_name -> money.
          levels: How many levels of child allocation to return (-1 = all).

        Returns:
        A list of ActualAllocation objects (for itself and any child classes
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
    def __init__(self, asset_classes):
        self._accounts = {}
        self.asset_classes = asset_classes.validate()
        self._leaf_asset_classes = asset_classes.leaves()

    def save(self, filename):
        with open(filename, 'w') as f:
            yaml.dump(self.to_dict(), f, sort_keys=False)

    @classmethod
    def load(cls, filename):
        with open(filename) as f:
            d = yaml.load(f.read(), Loader=yaml.SafeLoader)
        return Portfolio.from_dict(d)

    def to_dict(self):
        d = {'Asset Classes': self.asset_classes.to_dict()}
        if self._accounts:
            d['Accounts'] = [account.to_dict()
                             for account in self._accounts.values()]
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = Portfolio(AssetClass.from_dict(d.pop('Asset Classes')))
        for account_dict in d.pop('Accounts', []):
            ret_obj.add_account(Account.from_dict(account_dict))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def add_account(self, account, replace=False):
        for asset in account.assets():
            for asset_class in asset.class2ratio.keys():
                assert asset_class in self._leaf_asset_classes, (
                    f'Unknown or non-leaf asset class: {asset_class}')

        assert replace or account.name() not in self._accounts, (
            f'Attempting to add duplicate account: {account.name()}')

        self._accounts[account.name()] = account
        return self

    def remove_account(self, account_name):
        del self._accounts[account_name]

    def accounts(self):
        return self._accounts.values()

    def get_account(self, name):
        return self._accounts[name]

    def get_account_name_by_substr(self, account_str):
        """Returns account name whose name partially matches account_str.

        This method throws an AssertionError if more than one or none of the
        accounts match the account_str.
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
        """Returns a tuple account_name, asset_name where account name
        partially matches account_str and asset name partially matches
        asset_str or asset short name == asset_str
        Raises AssertionError if none or more than one asset matches the
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
        """Runs a whatif scenario if asset_name in account_name is changed by
        delta."""
        account = self.get_account(account_name)
        asset = account.get_asset(asset_name)
        asset.what_if(delta)
        # We take the money out of account.
        account.add_cash(-delta)

    def what_if_add_cash(self, account_name, cash_delta):
        self.get_account(account_name).add_cash(cash_delta)

    def get_what_ifs(self):
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
        for account in self.accounts():
            account.add_cash(-account.available_cash())
            for asset in account.assets():
                asset.what_if(-asset.get_what_if())

    def total_value(self):
        """Returns total of all assets added."""
        total = 0.0
        for account in self.accounts():
            total += account.available_cash()
            for asset in account.assets():
                total += asset.adjusted_value()
        return total

    # TODO: Renmame this to list_assets for consistency.
    def assets(self, short_name=False, quantity=False):
        """Returns all the assets."""
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
        """Returns all the lots in the portfolio as table.Table."""
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
        """Returns asset location as a list of [asset class, account_type,
        percentage, value]."""
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
        asset_class_to_value = {}

        for account in self.accounts():
            for asset in account.assets():
                for name, ratio in asset.class2ratio.items():
                    asset_class_to_value[name] = asset_class_to_value.get(
                        name, 0) + ratio * asset.adjusted_value()

        return asset_class_to_value

    def asset_allocation_tree(self, levels=-1):
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
        """Prints a 'compact' version of AA."""
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
