"""Top level interfaces and definitions for Lakshmi."""

from abc import ABC, abstractmethod


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
    self.class2ratio = class2ratio

    total = 0
    for ratio in class2ratio.values():
      if ratio < 0.0 or ratio > 1.0:
        raise ValidationError('Bad Class ratio provided to Asset ({})'.format(ratio))
      total += ratio

    if abs(total - 1.0) > 1e-6:
      raise ValidationError('Total allocation to classes must be 100% (actual = {}%)'.format(
        round(total*100)))

  @abstractmethod
  def Value(self):
    pass

  @abstractmethod
  def Name(self):
    pass

  def ToStr(self):
    return self.Name()


class Account():
  """Class representing an account.

  Arguments:
    name: Printable name for this account.
    type: Type of this account (TODO: Ideally an enum or class).
  """
  def __init__(self, name, account_type):
    self.name = name
    self.account_type = account_type
    self.assets = []

  def AddAsset(self, asset):
    self.assets.append(asset)
    return self

  def ToStr(self):
    return self.name


class AssetClass():
  """(Tree of) Asset classes."""
  def __init__(self, name):
    self.name = name
    self.children = []
    # Populated when _Validate is called.
    self._leaves = None

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

  def Leaves(self):
    if not self._leaves:
      raise ValidationError('Leaves() called on an non-validated asset class')

    return self._leaves

  def ValueMapped(self, money_allocation):
    """Returns how much money is mapped to this Asset Class or it's children.

    Arguments:
      money_allocation: A map of leaf_class_name -> money.
    """
    if not self._leaves:
      raise ValidationError('Need to validate AssetAllocation before using it.')

    return sum([value for name, value in money_allocation.items()
                if name in self._leaves])


  class Allocation():
    class Children:
      def __init__(self, name, actual_allocation, desired_allocation,
                   value_difference):
        self.name = name
        self.actual_allocation = actual_allocation
        self.desired_allocation = desired_allocation
        self.value_difference = value_difference

    def __init__(self, name, value):
      self.name = name
      self.value = value
      self.children = []

    def AddChild(self, name, actual, desired):
      self.children.append(
        self.Children(name, actual, desired, (desired - actual) * self.value))

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

    levels = (levels - 1) if levels > 0 else levels

    for asset_class, unused_ratio in self.children:
      ret_val += asset_class.ReturnAllocation(money_allocation, levels)

    return ret_val

class Interface():
  def __init__(self, asset_classes):
    self.accounts = []
    self.asset_classes = asset_classes.Validate()
    self._leaf_asset_classes = asset_classes.Leaves()

  def AddAccount(self, account):
    for asset in account.assets:
      for asset_class in asset.class2ratio.keys():
        if not asset_class in self._leaf_asset_classes:
          raise ValidationError('Unknown or non-leaf asset class: ' + asset_class)

    self.accounts.append(account)
    return self

  @staticmethod
  def DollarToStr(dollars):
    return '${:,.2f}'.format(dollars)

  def ListAssets(self):
    return_str_list = []
    total = 0.0

    for account in self.accounts:
      for asset in account.assets:
        return_str_list.append('{}, {}, '.format(account.ToStr(), asset.ToStr()))
        return_str_list.append('{}\n'.format(self.DollarToStr(asset.Value())))
        total += asset.Value()
    return_str_list.append('\nTotal: {}\n'.format(self.DollarToStr(total)))

    return ''.join(return_str_list)

  def AssetLocation(self):
    account_type_to_value = {}
    total = 0.0

    for account in self.accounts:
      for asset in account.assets:
        account_type_to_value[account.account_type] = account_type_to_value.get(
          account.account_type, 0) + asset.Value()
        total += asset.Value()

    return_str_list = []
    for account_type, value in account_type_to_value.items():
      return_str_list.append(account_type + ', ')
      return_str_list.append(self.DollarToStr(value)+ ', ')
      return_str_list.append('{}%\n'.format(round(100*value/total)))

    return ''.join(return_str_list)

  def AssetAllocation(self, levels = -1):
    asset_class_to_value = {}

    total = 0.0

    for account in self.accounts:
      for asset in account.assets:
        for name, ratio in asset.class2ratio.items():
          value = ratio * asset.Value()
          total += value
          asset_class_to_value[name] = asset_class_to_value.get(
            name, 0) + value

    return_str_list = []
    for alloc in self.asset_classes.ReturnAllocation(asset_class_to_value, levels):
      return_str_list += '{}: {}\n'.format(alloc.name, self.DollarToStr(alloc.value))
      for child in alloc.children:
        return_str_list += '{}: {}% ({}%), {}{}\n'.format(
          child.name,
          format(round(100*child.actual_allocation)),
          format(round(100*child.desired_allocation)),
          '-' if child.value_difference < 0 else '+',
          self.DollarToStr(abs(child.value_difference)))
      return_str_list += '\n'

    return_str_list.pop()
    return ''.join(return_str_list)
