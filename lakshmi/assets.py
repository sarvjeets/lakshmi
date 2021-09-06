"""Implementation of standard asset types."""

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
    return {asset.__class__.__name__: asset.to_dict()}


def from_dict(d):
    keys = list(d.keys())
    assert len(keys) == 1
    class_name = keys[0]

    for c in CLASSES:
        if c.__name__ == class_name:
            return c.from_dict(d.pop(class_name))

    raise AssertionError(f'Class {class_name} not found.')


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
            assert ratio >= 0.0 and ratio <= 1.0, (
                f'Bad Class ratio provided to Asset ({ratio})')
            total += ratio

        assert abs(total - 1.0) < 1e-6, (
            'Total allocation to classes must be 100% (actual = '
            f'{total * 100}%)')

    def to_dict(self):
        """Encodes this class into a dictionary.

        This method for non-abstract Asset classes encodes all data.
        This method for abstract Asset classes only encodes non-constructor
        data.
        """
        if self._delta != 0:
            return {'What if': self._delta}
        return dict()

    def from_dict(self, d):
        """Reverse of to_dict.

        This method for non-abstract Asset classes is a factory method.
        This method for abstract Asset classes decodes non-constructor
        data (if any).
        """
        self.what_if(d.pop('What if', 0))
        return self

    def to_table(self):
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
        return self.to_table().string(tablefmt='plain')

    def what_if(self, delta):
        self._delta += delta
        if abs(self._delta) < 1e-6:
            self._delta = 0

    def get_what_if(self):
        return self._delta

    def adjusted_value(self):
        return max(0, self.value() + self.get_what_if())

    @abstractmethod
    def value(self):
        pass

    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def short_name(self):
        pass


class ManualAsset(Asset):
    def __init__(self, name, value, class2ratio):
        assert value >= 0, 'Value of an asset can not be negative.'
        self._name = name
        self._value = value
        super().__init__(class2ratio)

    def to_dict(self):
        d = {'Name': self._name,
             'Value': self._value,
             'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = ManualAsset(d.pop('Name'),
                              d.pop('Value', 0),
                              d.pop('Asset Mapping'))
        Asset.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def value(self):
        return self._value

    def name(self):
        return self._name

    def short_name(self):
        return self._name


class TaxLot:
    """Class to represent a single tax lot for an Asset."""

    def __init__(self, date, quantity, unit_cost):
        # Do some sanity check.
        date_pattern = re.compile('\\d{4}/\\d{2}/\\d{2}')
        assert date_pattern.match(
            date), 'Tax lot dates should be in format YYYY/MM/DD'

        self.date = date
        self.quantity = quantity
        self.unit_cost = unit_cost

    def to_dict(self):
        return {'Date': self.date,
                'Quantity': self.quantity,
                'Unit Cost': self.unit_cost}

    @classmethod
    def from_dict(cls, d):
        ret_obj = TaxLot(d.pop('Date'), d.pop('Quantity'), d.pop('Unit Cost'))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj


class TradedAsset(Asset):
    """Abstract class representing an asset with units and per unit price."""

    def __init__(self, shares, class2ratio):
        self._shares = shares
        self._tax_lots = None
        super().__init__(class2ratio)

    def to_dict(self):
        d = dict()
        if self._tax_lots:
            d.update({'Tax Lots': [lot.to_dict() for lot in self._tax_lots]})
        d.update(super().to_dict())
        return d

    def from_dict(self, d):
        super().from_dict(d)
        if 'Tax Lots' not in d:
            return
        tax_lots_list = [TaxLot.from_dict(lot_dict)
                         for lot_dict in d.pop('Tax Lots')]
        self.set_lots(tax_lots_list)
        return self

    def shares(self):
        return self._shares

    def get_lots(self):
        return self._tax_lots

    def set_lots(self, tax_lots_list):
        sum_lots = sum([t.quantity for t in tax_lots_list])
        assert abs(sum_lots - self._shares) < 1e-6, (
            f'Lots provided should sum up to {self._shares}')
        self._tax_lots = tax_lots_list
        return self

    def list_lots(self):
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
        table = super().to_table()
        table.add_row(['Price:', f'{utils.format_money(self.price())}'])
        return table

    def string(self):
        if not self._tax_lots:
            return super().string()

        return (super().string() + '\n\nTax lots:\n'
                + f'{self.list_lots().string()}')

    def value(self):
        return self.shares() * self.price()

    # This class inherits abstract methods Name & short_name from Asset.

    @abstractmethod
    def price(self):
        pass


class NotFoundError(Exception):
    pass


class TickerAsset(TradedAsset, Cacheable):
    """An asset class representing a Ticker whose price can be pulled."""

    def __init__(self, ticker, shares, class2ratio):
        self._ticker = ticker
        session = requests.Session()
        session.headers['user-agent'] = (
            f'{lakshmi.constants.NAME}/{lakshmi.constants.VERSION}')
        self.yticker = yfinance.Ticker(ticker, session=session)
        super().__init__(shares, class2ratio)

    def to_dict(self):
        d = {'Ticker': self._ticker,
             'Shares': self.shares(),
             'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = TickerAsset(
            d.pop('Ticker'),
            d.pop('Shares'),
            d.pop('Asset Mapping'))
        TradedAsset.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def to_table(self):
        table = super().to_table()
        rows = table.list()
        rows.insert(0, ['Ticker:', f'{self._ticker}'])
        table.set_rows(rows)
        return table

    def cache_key(self):
        return self._ticker

    @cache(365)  # Name changes are rare.
    def name(self):
        if self.yticker.info.get('longName') is None:
            raise NotFoundError(
                f'Cannot retrieve ticker ("{self._ticker}") '
                'from Yahoo Finance')
        return self.yticker.info['longName']

    def short_name(self):
        return self._ticker

    @cache(1)
    def price(self):
        if self.yticker.info.get('regularMarketPrice') is None:
            raise NotFoundError(
                f'Cannot retrieve ticker ("{self._ticker}") '
                'from Yahoo Finance')
        return self.yticker.info['regularMarketPrice']


class VanguardFund(TradedAsset, Cacheable):
    """An asset class representing Vanguard trust fund represented by a
    numeric ID."""

    def __init__(self, fund_id, shares, class2ratio):
        self._fund_id = fund_id
        super().__init__(shares, class2ratio)

    def to_dict(self):
        d = {'Fund Id': self._fund_id,
             'Shares': self.shares(),
             'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = VanguardFund(
            d.pop('Fund Id'),
            d.pop('Shares'),
            d.pop('Asset Mapping'))
        TradedAsset.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def to_table(self):
        table = super().to_table()
        rows = table.list()
        rows.insert(0, ['Fund id:', f'{self._fund_id}'])
        table.set_rows(rows)
        return table

    def cache_key(self):
        return str(self._fund_id)

    @cache(365)  # Name changes are very rare.
    def name(self):
        req = requests.get(
            f'https://api.vanguard.com/rs/ire/01/pe/fund/{self._fund_id}'
            '/profile.json',
            headers={'Referer': 'https://vanguard.com/'})
        req.raise_for_status()  # Raise if error
        return req.json()['fundProfile']['longName']

    def short_name(self):
        return str(self._fund_id)

    @cache(1)
    def price(self):
        req = requests.get(
            f'https://api.vanguard.com/rs/ire/01/pe/fund/{self._fund_id}'
            '/price.json',
            headers={'Referer': 'https://vanguard.com/'})
        req.raise_for_status()  # Raise if error
        return float(req.json()['currentPrice']
                     ['dailyPrice']['regular']['price'])


class _TreasuryBonds(Asset):
    class Bond(Cacheable):
        """A class representing individual I or EE Bond."""

        def __init__(self, series, issue_date, denom):
            self.series = series
            self.issue_date = issue_date
            self.denom = denom
            self.redemption_date = datetime.datetime.now().strftime('%m/%Y')

        def cache_key(self):
            return '{}_{}_{}'.format(
                self.series,
                self.issue_date.replace('/', '.'),
                self.redemption_date.replace('/', '.'))

        @cache(32)  # The value of a Bond doesn't change in a month.
        def _get_bond_info(self):
            """Returns the rate and value of a $1000 bond."""
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
            unused_rate, value = self._get_bond_info()
            return value * (self.denom / 1000.0)

        def rate(self):
            rate, unused_value = self._get_bond_info()
            return rate

        def as_list(self):
            rate, value = self._get_bond_info()
            value *= (self.denom / 1000.0)
            return [self.issue_date, self.denom, rate, value]

    def __init__(self, series, class2ratio):
        self._series = series
        super().__init__(class2ratio)
        self._bonds = []

    def to_dict(self):
        d = {}
        d['Bonds'] = []
        for bond in self._bonds:
            d['Bonds'].append(
                {'Issue Date': bond.issue_date, 'Denomination': bond.denom})
        d.update(super().to_dict())
        return d

    def from_dict(self, d):
        for bond in d.pop('Bonds'):
            self.add_bond(bond.pop('Issue Date'), bond.pop('Denomination'))
            assert len(bond) == 0, ('Extra attributes found: '
                                    f'{list(bond.keys())}')
        Asset.from_dict(self, d)
        return self

    def bonds(self):
        return self._bonds

    def add_bond(self, issue_date, denom):
        self._bonds.append(self.Bond(self._series, issue_date, denom))
        return self

    def value(self):
        value = 0.0
        for bond in self._bonds:
            value += bond.value()
        return value

    def list_bonds(self):
        table = Table(
            4,
            headers=['Issue Date', 'Denom', 'Rate', 'Value'],
            coltypes=['str', 'dollars', 'str', 'dollars'])
        for bond in self._bonds:
            table.add_row(bond.as_list())
        return table

    def string(self):
        return (super().string() + '\n\nBonds:\n'
                + f'{self.list_bonds().string()}')

    def name(self):
        return f'{self._series} Bonds'

    def short_name(self):
        return self.name()


class IBonds(_TreasuryBonds):
    def __init__(self, class2ratio):
        super().__init__('I', class2ratio)

    def to_dict(self):
        d = {'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = IBonds(d.pop('Asset Mapping'))
        _TreasuryBonds.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj


class EEBonds(_TreasuryBonds):
    def __init__(self, class2ratio):
        super().__init__('EE', class2ratio)

    def to_dict(self):
        d = {'Asset Mapping': self.class2ratio}
        d.update(super().to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        ret_obj = EEBonds(d.pop('Asset Mapping'))
        _TreasuryBonds.from_dict(ret_obj, d)
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj


CLASSES = [ManualAsset, TickerAsset, VanguardFund, IBonds, EEBonds]
