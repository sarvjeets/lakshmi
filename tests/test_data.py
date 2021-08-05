"""Tests for lakshmi/data directory. Simply checks if the files parses."""
import lakshmi
import lakshmi.assets
from pathlib import Path
import unittest
import yaml

class DataTest(unittest.TestCase):
    def ParseDict(self, filename, function):
        file_path = (Path(__file__).parents[1].absolute() / filename)
        d = yaml.load(file_path.read_text(), Loader=yaml.SafeLoader)
        return function(d)

    def testAccount(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/Account.yaml',
            lakshmi.Account.FromDict))

    def testAssetClass(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/AssetClass.yaml',
            lakshmi.AssetClass.FromDict))

    def testEEBonds(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/EEBonds.yaml',
            lakshmi.assets.EEBonds.FromDict))

    def testIBonds(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/IBonds.yaml',
            lakshmi.assets.IBonds.FromDict))

    def testManualAsset(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/ManualAsset.yaml',
            lakshmi.assets.ManualAsset.FromDict))

    def testTickerAsset(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/TickerAsset.yaml',
            lakshmi.assets.TickerAsset.FromDict))

    def testVanguardFund(self):
        self.assertIsNotNone(self.ParseDict('lakshmi/data/VanguardFund.yaml',
            lakshmi.assets.VanguardFund.FromDict))

    def testPortfolio(self):
        self.assertIsNotNone(self.ParseDict('docs/portfolio.yaml',
            lakshmi.Portfolio.FromDict))


if __name__ == '__main__':
    unittest.main()
