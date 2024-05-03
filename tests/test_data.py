"""Tests for lakshmi/data directory. Simply checks if the files parses."""
import unittest
from pathlib import Path
from unittest.mock import patch

import ibonds
import yaml

import lakshmi
from lakshmi import utils


class DataTest(unittest.TestCase):
    def parse_dict(self, filename, function):
        file_path = (Path(__file__).parents[1].absolute() / filename)
        d = yaml.load(file_path.read_text(), Loader=utils.get_loader())
        return function(d)

    def test_account(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/Account.yaml',
                                             lakshmi.Account.from_dict))

    def test_asset_class(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/AssetClass.yaml',
                                             lakshmi.AssetClass.from_dict))

    def test_ee_bonds(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/EEBonds.yaml',
                                             lakshmi.assets.EEBonds.from_dict))

    @patch('lakshmi.assets.IBonds._InterestRates.get')
    def test_i_bonds(self, mock_get):
        INTEREST_RATE_DATA = """
        2020-11-01:
        - 0.00
        - 0.84
        2021-05-01:
        - 0.00
        - 1.77
        """
        mock_get.return_value = ibonds.InterestRates(INTEREST_RATE_DATA)
        self.assertIsNotNone(self.parse_dict('lakshmi/data/IBonds.yaml',
                                             lakshmi.assets.IBonds.from_dict))

    def test_manual_asset(self):
        self.assertIsNotNone(
            self.parse_dict(
                'lakshmi/data/ManualAsset.yaml',
                lakshmi.assets.ManualAsset.from_dict))

    def test_ticker_asset(self):
        self.assertIsNotNone(
            self.parse_dict(
                'lakshmi/data/TickerAsset.yaml',
                lakshmi.assets.TickerAsset.from_dict))

    def test_vanguard_fund(self):
        self.assertIsNotNone(
            self.parse_dict(
                'lakshmi/data/VanguardFund.yaml',
                lakshmi.assets.VanguardFund.from_dict))

    def test_checkpoint(self):
        self.assertIsNotNone(
            self.parse_dict(
                'lakshmi/data/Checkpoint.yaml',
                lambda x: lakshmi.performance.Checkpoint.from_dict(
                    x, date='2021/01/01')))

    def test_portfolio(self):
        self.assertIsNotNone(self.parse_dict('docs/portfolio.yaml',
                                             lakshmi.Portfolio.from_dict))


if __name__ == '__main__':
    unittest.main()
