"""Tests for lakshmi/data directory. Simply checks if the files parses."""
import lakshmi
import lakshmi.assets
from pathlib import Path
import unittest
import yaml

class DataTest(unittest.TestCase):
    def parse_dict(self, filename, function):
        file_path = (Path(__file__).parents[1].absolute() / filename)
        d = yaml.load(file_path.read_text(), Loader=yaml.SafeLoader)
        return function(d)

    def test_account(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/Account.yaml',
            lakshmi.Account.FromDict))

    def test_asset_class(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/AssetClass.yaml',
            lakshmi.AssetClass.FromDict))

    def test_ee_bonds(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/EEBonds.yaml',
            lakshmi.assets.EEBonds.FromDict))

    def test_i_bonds(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/IBonds.yaml',
            lakshmi.assets.IBonds.FromDict))

    def test_manual_asset(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/ManualAsset.yaml',
            lakshmi.assets.ManualAsset.FromDict))

    def test_ticker_asset(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/TickerAsset.yaml',
            lakshmi.assets.TickerAsset.FromDict))

    def test_vanguard_fund(self):
        self.assertIsNotNone(self.parse_dict('lakshmi/data/VanguardFund.yaml',
            lakshmi.assets.VanguardFund.FromDict))

    def test_portfolio(self):
        self.assertIsNotNone(self.parse_dict('docs/portfolio.yaml',
            lakshmi.Portfolio.FromDict))


if __name__ == '__main__':
    unittest.main()
