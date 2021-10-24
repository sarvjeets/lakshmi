"""This module contains implementation of all the standard asset types.
The top-level interface which every asset type must implement is
lakshmi.assets.Asset. This class also contains helper functions that
operate on an asset type.
"""

import datetime
import re
from abc import ABC, abstractmethod

import requests
import yfinance

import lakshmi.constants
import lakshmi.utils as utils
from lakshmi.cache import Cacheable, cache
from lakshmi.table import Table


def to_dict(asset):
    """Returns a dictionary representation of asset.

    This function is used to convert an 'asset' (aka a class implementing
    lakshmi.assets.Asset interface) into a dictionary. This is mainly used
    to serialize an asset type into a yaml-friendly format. The function
    lakshmi.assets.from_dict is an inverse of this function.

    Args:
        asset: An object of a class implementating lakshmi.assets.Asset
        interface.
    Returns: A dictionary representation of asset.
    """
    return {asset.__class__.__name__: asset.to_dict()}


def from_dict(d):
    """Converts a dictionary representing an asset into an asset object.

    This function is reverse of lakshmi.assets.to_dict function.

    Args:
        d: A dictionary representating an asset type.

    Returns: An object of class implementing lakshmi.assets.Asset interface
    corresponding to d.

    Raises: AssertionError if dict doesn't represent a lakshmi asset type.
    """
    keys = list(d.keys())
    assert len(keys) == 1
    class_name = keys[0]

    for c in CLASSES:
        if c.__name__ == class_name:
            return c.from_dict(d.pop(class_name))

    raise AssertionError(f'Class {class_name} not found.')


class Asset(ABC):
    """Top-level class representing an asset (fund, ETF, cash, etc.).

    Every asset type in lakshmi must inherit from this class.
    """

    def __init__(self, class2ratio):
        """
        Args:
          class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0

        Raises: AssertionError if ratio is not in (0, 1] or if the sum of
        ratio across all class_name is not equal to 1.
        """
        self._delta = 0
        self.class2ratio = class2ratio

        total = 0
        for ratio in class2ratio.values():
            assert ratio > 0.0 and ratio <= 1.0, (
                f'Bad Class ratio provided to Asset ({ratio})')
            total += ratio

        assert abs(total - 1.0) < 1e-6, (
            'Total allocation to classes must be 100% (actual = '
            f'{total * 100}%)')

    def to_dict(self):
        """Encodes this object into a dictionary.

        Convention: This method for non-abstract (leaf) Asset classes encodes
        all the fields present in the object. This method for abstract Asset
        classes only encodes fields that are not passed in the constructor
        during initialization of the object (encoding those fields is the
        responsibility of the sub-class).

        Returns: A dictionary object representing self.
        """
        if self._delta != 0:
            return {'What if': self._delta}
        return dict()

    def from_dict(self, d):
        """Reverse of to_dict.

        This function initializes the object of this class given a dictionary.
        Convention: This method for non-abstract Asset classes is a factory
        method (static function) that initializes and returns a new object.
        This method for abstract Asset classes decodes non-constructor data (if
        any) and modifies self.

        Args:
            d: A dictionary representing self.

        Returns: An object initialized with fields present in d.
        """
        self.what_if(d.pop('What if', 0))
        return self

    def to_table(self):
        """Returns a table representing this object.

        This function converts self object into a table
        suitable for pretty-printing.

        Returns: lakshmi.table.Table object representing the data in this
        class.
        """
        table = Table(2).add_row(['Name:', f'{self.name()}'])

        asset_mapping_table = Table(2, coltypes=['str', 'percentage'])
        for asset_class, ratio in self.class2ratio.items():
            asset_mapping_table.add_row([f'{asset_class}', ratio])
        table.add_row(['Asset Class Mapping:',
                       f'{asset_mapping_table.string(tablefmt="plain")}'])

        if self._delta:
            table.add_row(['Adjusted Value:',
                           f'{utils.format_money(self.adjusted_value())}'])
            table.add_row(
                ['What if:', f'{utils.format_money_delta(self._delta)}'])
        else:
            table.add_row(
                ['Value:', f'{utils.format_money(self.adjusted_value())}'])

        return table

    def string(self):
        """Returns a string representation of this object."""
        return self.to_table().string(tablefmt='plain')

    def what_if(self, delta):
        """Adds delta (what if) to the adjusted value of this asset.

        This function is provided to all assets and adds delta
        to the adjusted value (without changing number of shares, etc.). This
        is used to check how the asset allocation etc. would change if the
        value of this asset is changed. After verifying the changes, it's
        really easy to undo the changes by a call to what_if(-delta). A
        bit of warning: what_if(100) followed by what_if(100) will add
        200 to the value (i.e. the call doesn't reset any existing deltas
        that are already added to the value.

        Args:
            delta: A float to be added to the total value.
        """
        self._delta += delta
        if abs(self._delta) < 1e-6:
            self._delta = 0

    def get_what_if(self):
        """Returns any what ifs (delta) that are added to the value."""
        return self._delta

    def adjusted_value(self):
        """Returns the adjusted value (after adding any what ifs)."""
        return max(0, self.value() + self.get_what_if())

    @abstractmethod
    def value(self):
        """Returns the value of this asset."""
        pass

    @abstractmethod
    def name(self):
        """Returns the full name of this asset."""
        pass

    @abstractmethod
    def short_name(self):
        """Returns the short name of this asset (ideally < 10 chars)."""
        pass


class ManualAsset(Asset):
    """This is a special catch-all asset type that represents an asset whose
    value is manually specified and is not updated automatically."""
    def __init__(self, name, value, class2ratio):
        """
        Args:
            name: Full name of this asset (also is used as short name).
            value: The current value (in dollars, float) of this asset.
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0

        Raises: AssertionError if value is negative.
        """
        assert value >= 0, 'Value of an asset can not be negative.'
        self._name = name
        self._value = value
        super().__init__(class2ratio)

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Name': self._name,
             'Value': self._value,
             'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d.

        This is reverse of to_dict.
        Args:
            d: A dictionary (usually the output of to_dict).

        Returns: A new ManualAsset object.

        Raises: AssertionError if d cannot be parsed correctly.
        """
        ret_obj = ManualAsset(d.pop('Name'),
                              d.pop('Value', 0),
                              d.pop('Asset Mapping'))
        Asset.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def value(self):
        """Returns value of this asset."""
        return self._value

    def name(self):
        """Returns name of this asset."""
        return self._name

    def short_name(self):
        """Returns short name (same as name) of this asset."""
        return self._name


class TaxLot:
    """Class representing a single tax lot for an Asset."""

    def __init__(self, date, quantity, unit_cost):
        """
        Args:
            date: String representing date (YYYY/MM/DD) on which this lot was
            bought.
            quantity: Number of shares bought on date.
            unit_cost: Price per share.

        Raises: AssertionError if date is not in the right format.
        """
        # Do some sanity check.
        date_pattern = re.compile('\\d{4}/\\d{2}/\\d{2}')
        assert date_pattern.match(
            date), 'Tax lot dates should be in format YYYY/MM/DD'

        self.date = date
        self.quantity = quantity
        self.unit_cost = unit_cost

    def to_dict(self):
        """Converts this object into a dictionary."""
        return {'Date': self.date,
                'Quantity': self.quantity,
                'Unit Cost': self.unit_cost}

    @classmethod
    def from_dict(cls, d):
        """Factory method to return a new object representing a dictionary.

        This is reverse of to_dict. This function returns a newly initialized
        TaxLot object corresponding to d.

        Args:
            d: A dictionary representing TaxLot (usually output of to_dict)

        Returns: An initialied TaxLot object corresponding to d.

        Raises: AssertionError if d can't be parsed properly.
        """
        ret_obj = TaxLot(d.pop('Date'), d.pop('Quantity'), d.pop('Unit Cost'))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj


class TradedAsset(Asset):
    """Abstract class representing an asset that is traded on stock market.

    This asset is assumed to have 'shares' and per unit price and can
    optionally have tax lots."""

    def __init__(self, shares, class2ratio):
        """
        Args:
            shares: Number of shares of this asset.
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0
        """
        self._shares = shares
        self._tax_lots = None
        super().__init__(class2ratio)

    def to_dict(self):
        """Converts this asset into a dictionary."""
        d = dict()
        if self._tax_lots:
            d.update({'Tax Lots': [lot.to_dict() for lot in self._tax_lots]})
        d.update(super().to_dict())
        return d

    def from_dict(self, d):
        """Initializes self with data provided via dictionary d."""
        super().from_dict(d)
        if 'Tax Lots' not in d:
            return
        tax_lots_list = [TaxLot.from_dict(lot_dict)
                         for lot_dict in d.pop('Tax Lots')]
        self.set_lots(tax_lots_list)
        return self

    def shares(self):
        """Returns the number of shares."""
        return self._shares

    def get_lots(self):
        """Returns the tax lots or None if they are not set.

        Returns: A list of TaxLot or None if not set.
        """
        return self._tax_lots

    def set_lots(self, tax_lots_list):
        """Sets the tax lots.

        Args:
            tax_lots_list: A list of TaxLot representing all the tax_lots.

        Raises: AssertionError if the number of shares in the lots don't
        sum up to the number of shares in this asset.
        """
        sum_lots = sum([t.quantity for t in tax_lots_list])
        assert abs(sum_lots - self._shares) < 1e-6, (
            f'Lots provided should sum up to {self._shares}')
        self._tax_lots = tax_lots_list
        return self

    def list_lots(self):
        """Returns a table of tax lots.

        This function returns a Table of tax lots which can be used to
        pretty-print the tax lot information.

        Returns: lakshmi.table.Table object containing Date, Quantity,
        Cost, Gain and Gain% fields for all the lots.
        """
        table = Table(5,
                      headers=['Date', 'Quantity', 'Cost', 'Gain', 'Gain%'],
                      coltypes=['str', 'float', 'dollars', 'delta_dollars',
                                'percentage'])
        if not self._tax_lots:
            return table

        for lot in self._tax_lots:
            table.add_row(
                [lot.date,
                 lot.quantity,
                 lot.unit_cost * lot.quantity,
                 (self.price() - lot.unit_cost) * lot.quantity,
                 self.price() / lot.unit_cost - 1])
        return table

    def to_table(self):
        """Returns this asset as a lakshmi.table.Table object."""
        table = super().to_table()
        table.add_row(['Price:', f'{utils.format_money(self.price())}'])
        return table

    def string(self):
        """Returns this asset as a string."""
        if not self._tax_lots:
            return super().string()

        return (super().string() + '\n\nTax lots:\n'
                + f'{self.list_lots().string()}')

    def value(self):
        """Returns the current market value of this asset."""
        return self.shares() * self.price()

    # This class inherits abstract methods Name & short_name from Asset.

    @abstractmethod
    def price(self):
        """Returns the current market value of this asset."""
        pass


class NotFoundError(Exception):
    pass


class TickerAsset(TradedAsset, Cacheable):
    """An asset class represented by a Ticker whose price can be pulled."""

    def __init__(self, ticker, shares, class2ratio):
        """
        Args:
            ticker: Ticker of this asset (string),
            shares: Total number of shares.
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0
        """
        self._ticker = ticker
        session = requests.Session()
        session.headers['user-agent'] = (
            f'{lakshmi.constants.NAME}/{lakshmi.constants.VERSION}')
        self.yticker = yfinance.Ticker(ticker, session=session)
        super().__init__(shares, class2ratio)

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Ticker': self._ticker,
             'Shares': self.shares(),
             'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d.

        This is reverse of to_dict.
        Args:
            d: A dictionary (usually the output of to_dict).

        Returns: A new TradedAsset object.

        Raises: AssertionError if d cannot be parsed correctly.
        """
        ret_obj = TickerAsset(
            d.pop('Ticker'),
            d.pop('Shares'),
            d.pop('Asset Mapping'))
        TradedAsset.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def to_table(self):
        """Returns a table representing this object.

        This function converts this object into a table
        suitable for pretty-printing.

        Returns: lakshmi.table.Table object representing the data in this
        class.
        """
        table = super().to_table()
        rows = table.list()
        rows.insert(0, ['Ticker:', f'{self._ticker}'])
        table.set_rows(rows)
        return table

    def cache_key(self):
        """Unique key used for caching return values."""
        return self._ticker

    @cache(365)  # Name changes are rare.
    def name(self):
        """Returns full name of this asset.

        This function pulls the name corresponding to the ticker symbol
        of this asset. The return value is cached for 365 days.

        Returns: A string representing the name of this asset.

        Raises: NonFoundError if the ticker is not found.
        """
        asset_name = self.yticker.info.get('longName') or \
            self.yticker.info.get('shortName') or \
            self.yticker.info.get('name')

        if asset_name is None:
            raise NotFoundError(
                f'Cannot retrieve ticker ("{self._ticker}") '
                'from Yahoo Finance')
        return asset_name

    def short_name(self):
        """Returns the short name (ticker) of this object."""
        return self._ticker

    @cache(1)
    def price(self):
        """Returns the market price of this asset.

        The return price is cached for a day.

        Returns: Price (float).

        Raises: NotFoundError if the ticker is not found.
        """
        if self.yticker.info.get('regularMarketPrice') is None:
            raise NotFoundError(
                f'Cannot retrieve ticker ("{self._ticker}") '
                'from Yahoo Finance')
        return self.yticker.info['regularMarketPrice']


class VanguardFund(TradedAsset, Cacheable):
    """An asset class representing Vanguard trust fund represented by a
    numeric ID."""

    def __init__(self, fund_id, shares, class2ratio):
        """
        Args:
            fund_id: Integer representing the Fund Id.
            shares: Number of shares of this fund.
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0
        """
        self._fund_id = fund_id
        super().__init__(shares, class2ratio)

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Fund Id': self._fund_id,
             'Shares': self.shares(),
             'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d.

        This is reverse of to_dict.
        Args:
            d: A dictionary (usually the output of to_dict).

        Returns: A new VanguardFund object.

        Raises: AssertionError if d cannot be parsed correctly.
        """
        ret_obj = VanguardFund(
            d.pop('Fund Id'),
            d.pop('Shares'),
            d.pop('Asset Mapping'))
        TradedAsset.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def to_table(self):
        """Returns this asset as a lakshmi.table.Table object."""
        table = super().to_table()
        rows = table.list()
        rows.insert(0, ['Fund id:', f'{self._fund_id}'])
        table.set_rows(rows)
        return table

    def cache_key(self):
        """Unique key used for caching return values."""
        return str(self._fund_id)

    @cache(365)  # Name changes are very rare.
    def name(self):
        """Returns full name of this asset.

        This function returns the name of the fund corresponding to
        the fund id. The returned name is cached for 365 days.

        Returns: A string representing the name of this asset.

        Raises: AssertionError if the name cannot be fatched.
        """
        req = requests.get(
            f'https://api.vanguard.com/rs/ire/01/pe/fund/{self._fund_id}'
            '/profile.json',
            headers={'Referer': 'https://vanguard.com/'})
        req.raise_for_status()  # Raise if error
        return req.json()['fundProfile']['longName']

    def short_name(self):
        """Returns the short name (fund id, string) of this object."""
        return str(self._fund_id)

    @cache(1)
    def price(self):
        """Returns the market price of this asset.

        The return price is cached for a day.

        Returns: Price (float).

        Raises: AssertionError in case the price cannot be fetched.
        """
        req = requests.get(
            f'https://api.vanguard.com/rs/ire/01/pe/fund/{self._fund_id}'
            '/price.json',
            headers={'Referer': 'https://vanguard.com/'})
        req.raise_for_status()  # Raise if error
        return float(req.json()['currentPrice']
                     ['dailyPrice']['regular']['price'])


class _TreasuryBonds(Asset):
    """Class representing a collection of I or EE bonds."""
    class Bond(Cacheable):
        """A class representing individual I or EE Bond."""

        def __init__(self, series, issue_date, denom):
            """
            Args:
                series: Type of Bond, either 'I' or 'EE'.
                issue_date: String representing the issue month, in MM/YYYY
                format.
                denom: The denomination of this bond.
            """
            self.series = series
            self.issue_date = issue_date
            self.denom = denom
            self.redemption_date = datetime.datetime.now().strftime('%m/%Y')

        def cache_key(self):
            """Unique key used for caching return values."""
            return '{}_{}_{}'.format(
                self.series,
                self.issue_date.replace('/', '.'),
                self.redemption_date.replace('/', '.'))

        @cache(32)  # The value of a Bond doesn't change in a month.
        def _get_bond_info(self):
            """Returns the rate and value of a $1000 bond.

            Returns: A tuple representing the percentage rate and
            the current dollar value.
            """
            data = {
                'RedemptionDate': self.redemption_date,
                'Series': self.series,
                'Denomination': '1000',
                'IssueDate': self.issue_date,
                'btnAdd.x': 'CALCULATE'
            }

            req = requests.post(
                'http://www.treasurydirect.gov/BC/SBCPrice', data=data)
            req.raise_for_status()

            ret_vals = re.findall('\n<td>.*</td>', req.text)
            rate = re.sub('\n|<[^>]+>', '', ret_vals[6])
            value = float(re.sub('\n|\\$|,|<[^>]+>', '', ret_vals[7]))
            # EE Bonds returned are half the value (I guess TD website
            # assumes paper bonds)
            return rate, value * (2.0 if self.series == 'EE' else 1.0)

        def value(self):
            """Returns the current value of this bond."""
            unused_rate, value = self._get_bond_info()
            return value * (self.denom / 1000.0)

        def rate(self):
            """Returns the current percentage rate of this bond."""
            rate, unused_value = self._get_bond_info()
            return rate

        def as_list(self):
            """Returns this bond as a list.

            Returns: A list of Issue date, denomination, rate (as percentage)
            and current value.
            """
            rate, value = self._get_bond_info()
            value *= (self.denom / 1000.0)
            return [self.issue_date, self.denom, rate, value]

    def __init__(self, series, class2ratio):
        """
        Args:
            series: The type of the bonds, either 'I' or 'EE'.
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0
        """
        self._series = series
        super().__init__(class2ratio)
        self._bonds = []

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {}
        d['Bonds'] = []
        for bond in self._bonds:
            d['Bonds'].append(
                {'Issue Date': bond.issue_date, 'Denomination': bond.denom})
        d.update(super().to_dict())
        return d

    def from_dict(self, d):
        """Returns a new object specified by dictionary d.

        This is reverse of to_dict.

        Args:
            d: A dictionary (usually the output of to_dict).

        Returns: A new _TreasuryBonds object.

        Raises: AssertionError if d cannot be parsed correctly.
        """
        for bond in d.pop('Bonds'):
            self.add_bond(bond.pop('Issue Date'), bond.pop('Denomination'))
            assert len(bond) == 0, ('Extra attributes found: '
                                    f'{list(bond.keys())}')
        Asset.from_dict(self, d)
        return self

    def bonds(self):
        """Returns all bonds as list.

        Returns: A lot of self.Bond objects.
        """
        return self._bonds

    def add_bond(self, issue_date, denom):
        """Adds a new bond to this asset.

        Args:
            issue_date: String representing the issue date (in MM/YYYY format)
            denom: The denomination of this bond.
        """
        self._bonds.append(self.Bond(self._series, issue_date, denom))
        return self

    def value(self):
        """Returns the current market value of all the bonds."""
        value = 0.0
        for bond in self._bonds:
            value += bond.value()
        return value

    def list_bonds(self):
        """Returns all bonds as a table.

        Returns: A lakshmi.table.Table contains all the bonds in this asset.
        The columns correspond to Issue Date, Denomination, Rate as
        percentage, and current market value.
        """
        table = Table(
            4,
            headers=['Issue Date', 'Denom', 'Rate', 'Value'],
            coltypes=['str', 'dollars', 'str', 'dollars'])
        for bond in self._bonds:
            table.add_row(bond.as_list())
        return table

    def string(self):
        """Returns this asset as string."""
        return (super().string() + '\n\nBonds:\n'
                + f'{self.list_bonds().string()}')

    def name(self):
        """Returns the name of this asset (either 'I Bonds' or 'EE Bonds')."""
        return f'{self._series} Bonds'

    def short_name(self):
        """Returns short name (same as name)."""
        return self.name()


class IBonds(_TreasuryBonds):
    """Class representing a collection of I Bonds."""
    def __init__(self, class2ratio):
        """
        Args:
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0
        """
        super().__init__('I', class2ratio)

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d."""
        ret_obj = IBonds(d.pop('Asset Mapping'))
        _TreasuryBonds.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj


class EEBonds(_TreasuryBonds):
    def __init__(self, class2ratio):
        """
        Args:
            class2ratio: Dict of class_name -> ratio, where 0 < ratio <= 1.0
        """
        super().__init__('EE', class2ratio)

    def to_dict(self):
        """Returns a dict representing this object."""
        d = {'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object specified by dictionary d."""
        ret_obj = EEBonds(d.pop('Asset Mapping'))
        _TreasuryBonds.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj


# A list of all the assets type (classes) defined in this module.
CLASSES = [ManualAsset, TickerAsset, VanguardFund, IBonds, EEBonds]
