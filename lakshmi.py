"""Top level interfaces and definitions for Lakshmi."""

from abc import ABC, abstractmethod
import assets
from table import Table
import yaml


class ValidationError(Exception):
  """Exception raised when some validation failed."""
  pass


class Asset(ABC):
  """Class representing an asset (fund, ETF, cash, etc.)."""
  def __init__(self, class2ratio):
    """
    Argments:
      class2ratio: Dict of class_name -> ratio. 0 < Ratio <= 1.0
    """
    self._delta = 0
    self.class2ratio = class2ratio

    total = 0
    for ratio in class2ratio.values():
      if ratio < 0.0 or ratio > 1.0:
        raise ValidationError('Bad Class ratio provided to Asset ({})'.format(ratio))
      total += ratio

    if abs(total - 1.0) > 1e-6:
      raise ValidationError(
        'Total allocation to classes must be 100% (actual = {}%)'.format(
          round(total*100)))

  def ToDict(self):
    """Encodes this class into a dictionary.

    This method for non-abstract Asset classes encodes all data.
    This method for abstract Asset classes only encodes non-constructor data.
    """
    if self._delta != 0:
      return {'What if': self._delta}
    return dict()

  def FromDict(self, d):
    """Reverse of ToDict.

    This method for non-abstract Asset classes is a factory method.
    This method for abstract Asset classes decodes non-constructor data (if any).
    """
    self.WhatIf(d.pop('What if', 0))
    return self

  def WhatIf(self, delta):
    self._delta += delta

  def AdjustedValue(self):
    return self.Value() + self._delta

  @abstractmethod
  def Value(self):
    pass

  @abstractmethod
  def Name(self):
    pass

  @abstractmethod
  def ShortName(self):
    pass


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
    d = {'Name' : self._name,
         'Account Type': self.account_type,
         'Assets' : [assets.ToDict(asset) for asset in self._assets.values()]}
    if self._cash != 0:
      d['Available Cash'] = self._cash
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = Account(d.pop('Name'), d.pop('Account Type'))
    for asset_dict in d.pop('Assets'):
      ret_obj.AddAsset(assets.FromDict(asset_dict))
    ret_obj._cash = d.pop('Available Cash', 0)
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def AddAsset(self, asset):
    if asset.ShortName() in self._assets:
      raise ValidationError('Attempting to add duplicate Asset: ' +
                            asset.ShortName())
    self._assets[asset.ShortName()] = asset
    return self

  def Assets(self):
    return self._assets.values()

  def GetAsset(self, short_name):
    return self._assets[short_name]

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
      d['Children'] = [{'Ratio': ratio, 'Asset Class': child.ToDict()}
                       for child, ratio in self.children]
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = AssetClass(d.pop('Name'))
    for child_dict in d.pop('Children', []):
      ret_obj.AddSubClass(
        child_dict.pop('Ratio'),
        AssetClass.FromDict(child_dict.pop('Asset Class')))
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
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
      if ratio < 0.0 or ratio > 1.0:
        raise ValidationError('Bad ratio provided to Asset Class ({})'.format(ratio))
      total += ratio
      temp_leafs, temp_classes = asset_class._Validate()
      self._leaves.update(temp_leafs)
      class_names += temp_classes

    if abs(total - 1) > 1e-6:
      raise ValidationError('Sum of sub-classes is not 100% (actual: {}%)'.format(total*100))

    return self._leaves, class_names

  def Validate(self):
    unused_leaves, all_class_names = self._Validate()
    duplicates = set([x for x in all_class_names if all_class_names.count(x) > 1])

    if duplicates:
      raise ValidationError('Found duplicate Asset class(es): ' + str(duplicates))

    return self

  def _Check(self):
    if not self._leaves:
      raise ValidationError('Need to validate AssetAllocation before using it.')

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
      def __init__(self, name, actual_allocation, desired_allocation, value,
                   value_difference):
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
        self.Children(name,
                      actual,
                      desired,
                      actual * self.value,
                      (desired - actual) * self.value))

  def ReturnAllocation(self, money_allocation, levels = -1):
    """Returns actual and desired allocation based on how money is allocated.

    Arguments:
      money_allocation: A map of leaf_class_name -> money.
      levels: How many levels of child allocation to return (-1 = all).

    Returns:
    A list of ActualAllocation objects (for itself and any children classes
    based on levels flag.
    """
    value = self.ValueMapped(money_allocation)
    actual_alloc = self.Allocation(self.name, value)

    if value == 0:
      return [actual_alloc]

    for asset_class, desired_ratio in self.children:
      actual_ratio = asset_class.ValueMapped(money_allocation) / value
      actual_alloc.AddChild(asset_class.name, actual_ratio, desired_ratio)

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
    f = open(filename, 'w')
    yaml.dump(self.ToDict(), f, sort_keys=False)
    f.close()

  @classmethod
  def Load(cls, filename):
    f = open(filename, 'r')
    d = yaml.load(f.read(), Loader=yaml.SafeLoader)
    return Portfolio.FromDict(d)

  def ToDict(self):
    d = {'Asset Classes': self.asset_classes.ToDict()}
    if self._accounts:
      d['Accounts'] = [account.ToDict() for account in self._accounts.values()]
    return d

  @classmethod
  def FromDict(cls, d):
    ret_obj = Portfolio(AssetClass.FromDict(d.pop('Asset Classes')))
    for account_dict in d.pop('Accounts', []):
      ret_obj.AddAccount(Account.FromDict(account_dict))
    assert len(d) == 0, 'Extra attributes found: ' + str(list(d.keys()))
    return ret_obj

  def AddAccount(self, account):
    for asset in account.Assets():
      for asset_class in asset.class2ratio.keys():
        if not asset_class in self._leaf_asset_classes:
          raise ValidationError('Unknown or non-leaf asset class: ' + asset_class)

    if account.Name() in self._accounts:
      raise ValidationError('Attempting to add duplicate account: ' + account.Name())

    self._accounts[account.Name()] = account
    return self

  def Accounts(self):
    return self._accounts.values()

  def GetAccount(self, name):
    return self._accounts[name]

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
      coltypes = [None, 'delta_dollars'])
    asset_whatifs = Table(
      3,
      headers = ['Account', 'Asset', 'Delta'],
      coltypes = [None, None, 'delta_dollars'])

    for account in self.Accounts():
      if account.AvailableCash() != 0.0:
        account_whatifs.AddRow([account.Name(), account.AvailableCash()])
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

  def Assets(self):
    """Returns all the assets."""
    table = Table(3,
                  headers = ['Account', 'Asset', 'Value'],
                  coltypes = [None, None, 'dollars'])
    for account in self.Accounts():
      for asset in account.Assets():
        table.AddRow(
          [account.Name(),
           asset.Name(),
           asset.AdjustedValue()])
    return table

  def AssetLocation(self):
    """Returns asset location as a list of [account_type, value, percentage]."""
    account_type_to_value = {}
    total = 0.0

    for account in self.Accounts():
      account_type_to_value[account.account_type] = account_type_to_value.get(
        account.account_type, 0) + account.AvailableCash()
      total += account.AvailableCash()
      for asset in account.Assets():
        account_type_to_value[account.account_type] = account_type_to_value.get(
          account.account_type, 0) + asset.AdjustedValue()
        total += asset.AdjustedValue()

    table = Table(3,
                  headers = ['Account Type', 'Value', '%'],
                  coltypes = [None, 'dollars', 'percentage'])
    for account_type, value in account_type_to_value.items():
      table.AddRow([account_type, value, value/total])
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
                  headers = ['Class', 'Actual%', 'Desired%', 'Value'],
                  coltypes = [None, 'percentage', 'percentage', 'dollars'])
    for alloc in self.asset_classes.ReturnAllocation(self._GetAssetClassToValue(), levels):
      if not alloc.children:
        continue

      table.AddRow(['-\n{}:'.format(alloc.name)])
      for child in alloc.children:
        table.AddRow([child.name,
                      child.actual_allocation,
                      child.desired_allocation,
                      child.value])
    return table

  def AssetAllocation(self, asset_class_list):
    asset_class_ratio = map(self.asset_classes.FindAssetClass,
                            asset_class_list)
    flat_asset_class = AssetClass('Root')
    for asset_class, ratio in asset_class_ratio:
      flat_asset_class.AddSubClass(ratio, asset_class)

    try:
      flat_asset_class.Validate()
    except ValidationError:
      raise ValidationError(
        'AssetAllocation called with overlapping Asset Classes or ' +
        'Asset Classes which does not cover the full tree.')

    alloc = flat_asset_class.ReturnAllocation(self._GetAssetClassToValue(), 0)[0]
    table = Table(
      5,
      headers = ['Class', 'Actual%', 'Desired%', 'Value', 'Difference'],
      coltypes = [None, 'percentage', 'percentage', 'dollars', 'delta_dollars'])
    for child in alloc.children:
      table.AddRow(
        [child.name,
         child.actual_allocation,
         child.desired_allocation,
         child.value,
         child.value_difference])
    return table

  def AssetAllocationCompact(self):
    """Prints a 'compact' version of AA (Authors' favorite way of viewing his AA)."""
    def FindIndex(class_name, ret_list):
      # We assume ret_list has atleast one entry.
      names_list = [row[-3] for row in ret_list]
      return names_list.index(class_name)

    ret_list = []
    for alloc in self.asset_classes.ReturnAllocation(self._GetAssetClassToValue()):
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
          ret_list.insert(index + 1, [''] * len(ret_list[index]))
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
    for leaf_row in leaf_aa.List(): # Format: Class, A%, D%, Value, Diff
      ret_list_row = ret_list[FindIndex(leaf_row[0], ret_list)]
      ret_list_row.extend([''] * (cols - len(ret_list_row)))
      ret_list_row.extend(leaf_row[1:])

    # All done, now build the table.
    t = Table(
      cols + 4,
      headers = ['Class', 'A%', 'D%'] * int(cols/3) + leaf_aa.Headers()[1:],
      coltypes = [None, 'percentage', 'percentage'] * int(cols/3) + [
        'percentage', 'percentage', 'dollars', 'delta_dollars'])
    t.SetRows(ret_list)
    return t
