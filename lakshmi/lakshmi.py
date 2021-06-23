"""Top level interfaces and definitions for Lakshmi."""

from lakshmi.assets import FromDict, ToDict
from lakshmi.table import Table
import lakshmi.utils as utils
import yaml


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

    def ToDict(self):
        d = {'Name': self._name,
             'Account Type': self.account_type}
        if self._assets:
             d['Assets'] = [ToDict(asset) for asset in self._assets.values()]
        if self._cash != 0:
            d['Available Cash'] = self._cash
        return d

    @classmethod
    def FromDict(cls, d):
        ret_obj = Account(d.pop('Name'), d.pop('Account Type'))
        for asset_dict in d.pop('Assets', []):
            ret_obj.AddAsset(FromDict(asset_dict))
        ret_obj._cash = d.pop('Available Cash', 0)
        assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
        return ret_obj

    def String(self):
        table = Table(2)
        table.AddRow(['Name:', f'{self._name}'])
        table.AddRow(['Type:', f'{self.account_type}'])
        total = sum([asset.AdjustedValue() for asset in self._assets.values()])
        table.AddRow(['Total:', utils.FormatMoney(total)])
        if self._cash:
            table.AddRow(['Available Cash:', utils.FormatMoneyDelta(self._cash)])
        return table.String(tablefmt='plain')

    def AddAsset(self, asset, replace=False):
        assert replace or asset.ShortName() not in self._assets, (
            f'Attempting to add duplicate Asset: {asset.ShortName()}')
        self._assets[asset.ShortName()] = asset
        return self

    def Assets(self):
        return self._assets.values()

    def SetAssets(self, assets):
        self._assets = {}
        for asset in assets:
            self.AddAsset(asset)

    def GetAsset(self, short_name):
        return self._assets[short_name]

    def RemoveAsset(self, short_name):
        del self._assets[short_name]

    def Name(self):
        return self._name

    def AddCash(self, delta):
        self._cash += delta

    def AvailableCash(self):
        return self._cash


class AssetClass:
    """(Tree of) Asset classes."""
    def __init__(self, name):
        self.name = name
        self.children = []
        # Populated when _Validate is called.
        self._leaves = None

    def ToDict(self):
        d = {'Name': self.name}
        if self.children:
            d['Children'] = [{'Ratio': ratio} | child.ToDict()
                             for child, ratio in self.children]
        return d

    @classmethod
    def FromDict(cls, d):
        ret_obj = AssetClass(d.pop('Name'))
        for child_dict in d.pop('Children', []):
            ret_obj.AddSubClass(
                child_dict.pop('Ratio'),
                AssetClass.FromDict(child_dict))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj.Validate()

    def Copy(self):
        """Returns a copy of this AssetClass and its sub-classes."""
        ret_val = AssetClass(self.name)
        for child, ratio in self.children:
            ret_val.AddSubClass(ratio, child.Copy())
        return ret_val

    def AddSubClass(self, ratio, asset_class):
        self.children.append((asset_class, ratio))
        # Leaves is not upto date now, need validation again.
        self._leaves = None
        return self

    def _Validate(self):
        """Returns a tuple (leaf names, class names) for the subtree."""
        # Check if all percentages add up to 100%
        if not self.children:
            self._leaves = {self.name}
            return self._leaves, [self.name]

        self._leaves = set()
        class_names = [self.name]
        total = 0.0
        for asset_class, ratio in self.children:
            assert ratio >= 0.0 and ratio <= 1.0, (
                    f'Bad ratio provided to Asset Class ({ratio})')
            total += ratio
            temp_leafs, temp_classes = asset_class._Validate()
            self._leaves.update(temp_leafs)
            class_names += temp_classes

        assert abs(total - 1) < 1e-6, (
            f'Sum of sub-classes is not 100% (actual: {total * 100}%)')

        return self._leaves, class_names

    def Validate(self):
        unused_leaves, all_class_names = self._Validate()
        duplicates = set([x for x in all_class_names
                          if all_class_names.count(x) > 1])

        assert not duplicates, f'Found duplicate Asset class(es): {duplicates}'
        return self

    def _Check(self):
        assert self._leaves, 'Need to validate AssetAllocation before using it.'

    def FindAssetClass(self, asset_class_name):
        """Returns a tuple of object representing asset_class_name and its desired ratio.

        Returns None if asset_class_name is not found."""
        self._Check()

        if self.name == asset_class_name:
            return self, 1.0

        for asset_class, ratio in self.children:
            ret_value = asset_class.FindAssetClass(asset_class_name)
            if ret_value:
                return ret_value[0], ret_value[1] * ratio

        return None

    def Leaves(self):
        self._Check()
        return self._leaves

    def ValueMapped(self, money_allocation):
        """Returns how much money is mapped to this Asset Class or it's children.

        Arguments:
          money_allocation: A map of leaf_class_name -> money.
        """
        self._Check()
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

        def AddChild(self, name, actual, desired):
            self.children.append(
                self.Children(name, actual, desired, actual * self.value,
                    (desired - actual) * self.value))

    def ReturnAllocation(self, money_allocation, levels=-1):
        """Returns actual and desired allocation based on how money is allocated.

        Arguments:
          money_allocation: A map of leaf_class_name -> money.
          levels: How many levels of child allocation to return (-1 = all).

        Returns:
        A list of ActualAllocation objects (for itself and any child classes
        based on the levels flag).
        """
        value = self.ValueMapped(money_allocation)
        actual_alloc = self.Allocation(self.name, value)

        if value == 0:
            return [actual_alloc]

        for asset_class, desired_ratio in self.children:
            actual_ratio = asset_class.ValueMapped(money_allocation) / value
            actual_alloc.AddChild(
                asset_class.name,
                actual_ratio,
                desired_ratio)

        ret_val = [actual_alloc]

        if levels == 0:
            return ret_val

        if levels > 0:
            levels -= 1

        for asset_class, unused_ratio in self.children:
            ret_val += asset_class.ReturnAllocation(money_allocation, levels)

        return ret_val


class Portfolio:
    def __init__(self, asset_classes):
        self._accounts = {}
        self.asset_classes = asset_classes.Validate()
        self._leaf_asset_classes = asset_classes.Leaves()

    def Save(self, filename):
        with open(filename, 'w') as f:
            yaml.dump(self.ToDict(), f, sort_keys=False)

    @classmethod
    def Load(cls, filename):
        with open(filename) as f:
            d = yaml.load(f.read(), Loader=yaml.SafeLoader)
        return Portfolio.FromDict(d)

    def ToDict(self):
        d = {'Asset Classes': self.asset_classes.ToDict()}
        if self._accounts:
            d['Accounts'] = [account.ToDict()
                             for account in self._accounts.values()]
        return d

    @classmethod
    def FromDict(cls, d):
        ret_obj = Portfolio(AssetClass.FromDict(d.pop('Asset Classes')))
        for account_dict in d.pop('Accounts', []):
            ret_obj.AddAccount(Account.FromDict(account_dict))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def AddAccount(self, account, replace=False):
        for asset in account.Assets():
            for asset_class in asset.class2ratio.keys():
                assert asset_class in self._leaf_asset_classes, (
                    f'Unknown or non-leaf asset class: {asset_class}')

        assert replace or account.Name() not in self._accounts, (
            f'Attempting to add duplicate account: {account.Name()}')

        self._accounts[account.Name()] = account
        return self

    def RemoveAccount(self, account_name):
        del self._accounts[account_name]

    def Accounts(self):
        return self._accounts.values()

    def GetAccount(self, name):
        return self._accounts[name]

    def GetAccountNameBySubStr(self, account_str):
        """Returns account name who name partially matches account_str.

        This method throws an AssertionError if more than one or none of the
        accounts match the account_str.
        """

        matched_accounts = list(filter(lambda x: x.count(account_str),
                [account.Name() for account in self.Accounts()]))
        if len(matched_accounts) == 0:
            raise AssertionError(f'{account_str} does not match any account '
                    'in the portfolio')
        if len(matched_accounts) > 1:
            raise AssertionError(f'{account_str} matches more than one '
                        'account in the portfolio')
        return matched_accounts[0]

    def GetAssetNameBySubStr(self, account_str='', asset_str=''):
        """Returns a tuple account_name, asset_name where account name
        partially matches account_str and asset name partially matches
        asset_str or asset short name == asset_str
        Raises AssertionError if none or more than one asset matches the
        sub-strings."""
        matched_assets = list(filter(
                lambda x: x[0].count(account_str) and (
                    x[1].count(asset_str) or x[2] == asset_str),
                [(account.Name(), asset.Name(), asset.ShortName())
                    for account in self.Accounts()
                    for asset in account.Assets()]))
        if len(matched_assets) < 1:
            raise AssertionError('Provided asset and account strings match none '
                    'of the assets.')
        if len(matched_assets) > 1:
            raise AssertionError('Provided asset and account strings match more '
                    'than one assets.')
        return matched_assets[0][0], matched_assets[0][2]

    def WhatIf(self, account_name, asset_name, delta):
        """Runs a whatif scenario if asset_name in account_name is changed by delta."""
        account = self.GetAccount(account_name)
        asset = account.GetAsset(asset_name)
        asset.WhatIf(delta)
        # We take the money out of account.
        account.AddCash(-delta)

    def WhatIfAddCash(self, account_name, cash_delta):
        self.GetAccount(account_name).AddCash(cash_delta)

    def GetWhatIfs(self):
        account_whatifs = Table(
            2,
            headers=['Account', 'Cash'],
            coltypes=['str', 'delta_dollars'])
        asset_whatifs = Table(
            3,
            headers=['Account', 'Asset', 'Delta'],
            coltypes=['str', 'str', 'delta_dollars'])

        for account in self.Accounts():
            if account.AvailableCash() != 0.0:
                account_whatifs.AddRow(
                    [account.Name(), account.AvailableCash()])
            for asset in account.Assets():
                delta = asset.AdjustedValue() - asset.Value()
                if delta != 0.0:
                    asset_whatifs.AddRow([account.Name(), asset.Name(), delta])

        return account_whatifs, asset_whatifs

    def ResetWhatIfs(self):
        for account in self.Accounts():
            account.AddCash(-account.AvailableCash())
            for asset in account.Assets():
                asset.WhatIf(asset.Value() - asset.AdjustedValue())

    def TotalValue(self):
        """Returns total of all assets added."""
        total = 0.0
        for account in self.Accounts():
            total += account.AvailableCash()
            for asset in account.Assets():
                total += asset.AdjustedValue()
        return total

    def Assets(self, short_name=False, quantity=False):
        """Returns all the assets."""
        table = Table(
                3 + short_name + quantity,
                headers=['Account'] +
                        (['Name'] if short_name else []) +
                        (['Quantity'] if quantity else []) +
                        ['Asset', 'Value'],
                coltypes=['str'] +
                         (['str'] if short_name else []) +
                         (['float'] if quantity else []) +
                         ['str', 'dollars'])
        for account in self.Accounts():
            for asset in account.Assets():
                row = ([account.Name()] +
                        ([f'{asset.ShortName()}'] if short_name else []) +
                        [asset.Name(), asset.AdjustedValue()])
                if quantity:
                    row.insert(1 + short_name, asset.shares
                            if hasattr(asset, 'shares') else None)
                table.AddRow(row)

        return table

    def AssetLocation(self):
        """Returns asset location as a list of [asset class, account_type, percentage, value]."""
        class2type = {}  # Mapping of asset class -> account type -> money
        for account in self.Accounts():
            for asset in account.Assets():
                for name, ratio in asset.class2ratio.items():
                    if not name in class2type:
                        class2type[name] = {}
                    class2type[name][account.account_type] = class2type[name].get(
                            account.account_type, 0) + ratio * asset.AdjustedValue()

        table = Table(
                4,
                headers=['Asset Class', 'Account Type', 'Percentage', 'Value'],
                coltypes=['str', 'str', 'percentage', 'dollars'])

        for asset_class, type2value in class2type.items():
            first = True
            total = sum(type2value.values())
            if abs(total) < 1e-6:
                continue
            for account_type, value in sorted(type2value.items(), key=lambda x: x[1], reverse=True):
                table.AddRow([asset_class if first else '', account_type,
                    value / total, value])
                first = False
        return table

    def _GetAssetClassToValue(self):
        asset_class_to_value = {}

        for account in self.Accounts():
            for asset in account.Assets():
                for name, ratio in asset.class2ratio.items():
                    asset_class_to_value[name] = asset_class_to_value.get(
                        name, 0) + ratio * asset.AdjustedValue()

        return asset_class_to_value

    def AssetAllocationTree(self, levels=-1):
        table = Table(4,
                      headers=['Class', 'Actual%', 'Desired%', 'Value'],
                      coltypes=['str', 'percentage', 'percentage', 'dollars'])
        first_row = True
        for alloc in self.asset_classes.ReturnAllocation(
                self._GetAssetClassToValue(), levels):
            if not alloc.children:
                continue

            if not first_row:
                table.AddRow([' '])
            first_row = False
            table.AddRow([f'{alloc.name}:'])
            for child in alloc.children:
                table.AddRow([child.name,
                              child.actual_allocation,
                              child.desired_allocation,
                              child.value])
        return table

    def AssetAllocation(self, asset_class_list):
        flat_asset_class = AssetClass('Root')
        for asset_class in asset_class_list:
            found = self.asset_classes.FindAssetClass(asset_class)
            assert found, f'Could not find {asset_class}'
            flat_asset_class.AddSubClass(found[1], found[0])

        try:
            flat_asset_class.Validate()
        except AssertionError:
            raise AssertionError('AssetAllocation called with overlapping '
                    'Asset Classes or Asset Classes which does not cover the '
                    'full tree.') from None

        alloc = flat_asset_class.ReturnAllocation(
            self._GetAssetClassToValue(), 0)[0]
        table = Table(
            5,
            headers=['Class', 'Actual%', 'Desired%', 'Value', 'Difference'],
            coltypes=['str', 'percentage', 'percentage', 'dollars',
                      'delta_dollars'])
        for child in alloc.children:
            table.AddRow([child.name, child.actual_allocation,
                          child.desired_allocation, child.value,
                          child.value_difference])
        return table

    def AssetAllocationCompact(self):
        """Prints a 'compact' version of AA (Authors' favorite way of viewing his AA)."""
        def FindIndex(class_name, ret_list):
            # We assume ret_list has atleast one entry.
            names_list = [row[-3] for row in ret_list]
            return names_list.index(class_name)

        ret_list = []
        for alloc in self.asset_classes.ReturnAllocation(
                self._GetAssetClassToValue()):
            if not alloc.children:
                continue

            if not ret_list:
                for child in alloc.children:
                    ret_list.append([child.name,
                                     child.actual_allocation,
                                     child.desired_allocation])
            else:  # Parent is already in ret_list
                index = FindIndex(alloc.name, ret_list)
                # We know that here is atleast one child.
                for i in range(len(alloc.children) - 1):
                    # Make room for rest of the children by inserting empty extra rows of the
                    # same size as the parent's row
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
        leaf_aa = self.AssetAllocation(self.asset_classes.Leaves())
        for leaf_row in leaf_aa.List():  # Format: Class, A%, D%, Value, Diff
            ret_list_row = ret_list[FindIndex(leaf_row[0], ret_list)]
            ret_list_row.extend([None] * (cols - len(ret_list_row)))
            ret_list_row.extend(leaf_row[1:])

        # All done, now build the table.
        t = Table(cols + 4,
                  headers=['Class', 'A%', 'D%'] * int(cols / 3) +
                  leaf_aa.Headers()[1:],
                  coltypes=['str', 'percentage', 'percentage'] * int(cols / 3) +
                  ['percentage', 'percentage', 'dollars', 'delta_dollars'])
        t.SetRows(ret_list)
        return t
