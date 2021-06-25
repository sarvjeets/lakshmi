"""Tests for lakshmi/data directory. Simply checks if the files parses."""
import lakshmi
import lakshmi.assets
from pathlib import Path
import unittest
import yaml

class DataTest(unittest.TestCase):
    def ParseDict(self, filename, function):
        file_path = (Path(__file__).parents[1].absolute() /
                'data' / filename)
        non_commented_str = file_path.read_text().replace('\n# ', '\n')
        d = yaml.load(non_commented_str, Loader=yaml.SafeLoader)
        return function(d)

    def testAccount(self):
        self.assertIsNotNone(self.ParseDict('Account.yaml',
            lakshmi.Account.FromDict))

    def testAssetClass(self):
        self.assertIsNotNone(self.ParseDict('AssetClass.yaml',
            lakshmi.AssetClass.FromDict))

    def testEEBonds(self):
        self.assertIsNotNone(self.ParseDict('EEBonds.yaml',
            lakshmi.assets.EEBonds.FromDict))

    def testIBonds(self):
        self.assertIsNotNone(self.ParseDict('IBonds.yaml',
            lakshmi.assets.IBonds.FromDict))

    def testManualAsset(self):
        self.assertIsNotNone(self.ParseDict('ManualAsset.yaml',
            lakshmi.assets.ManualAsset.FromDict))

    def testTickerAsset(self):
        self.assertIsNotNone(self.ParseDict('TickerAsset.yaml',
            lakshmi.assets.TickerAsset.FromDict))

    def testVanguardFund(self):
        self.assertIsNotNone(self.ParseDict('VanguardFund.yaml',
            lakshmi.assets.VanguardFund.FromDict))


if __name__ == '__main__':
    unittest.main()