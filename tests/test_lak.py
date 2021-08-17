"""Tests for lakshmi.lak application."""
import click
from lakshmi import Portfolio, AssetClass, Account, lak
from lakshmi.assets import ManualAsset
import unittest
from unittest.mock import patch
from click.testing import CliRunner
from pathlib import Path

class TestLakContext(lak.LakContext):
    """A testing version of LakContext that doesn't load or save
    portfolio."""
    def __init__(self):
        self.portfolio_filename = 'test_portfolio.yaml'
        self.continued = False
        self.whatifs = None
        self.tablefmt = None
        self.saved = False

        self.portfolio = Portfolio(
            AssetClass('All')
            .AddSubClass(0.5, AssetClass('Stocks'))
            .AddSubClass(0.5, AssetClass('Bonds'))).AddAccount(
                    Account('Schwab', 'Taxable').AddAsset(
                        ManualAsset('Test Asset', 100.0, {'Stocks': 1.0})))

    def Portfolio(self):
        return self.portfolio

    def SavePortfolio(self):
        self.saved = True

    def Reset(self):
        """Reset the state for a new command (except the portfolio)."""
        self.continued = False
        self.whatifs = None
        self.tablefmt = None
        self.saved = False

def RunLak(args):
    return CliRunner().invoke(lak.lak, args.split(' '))

class LakTest(unittest.TestCase):
    def setUp(self):
        lak.lakctx = TestLakContext()

    @patch('lakshmi.lak.LakContext._ReturnConfig')
    @patch('lakshmi.cache')
    @patch('pathlib.Path.exists')
    def testLakContextInitWithNoConfig(
            self, MockExists, MockCache, MockReturnConfig):
        MockReturnConfig.return_value = {}
        MockExists.return_value = True

        lakctx = lak.LakContext()
        self.assertFalse(lakctx.continued)
        self.assertIsNone(lakctx.whatifs)
        self.assertIsNone(lakctx.portfolio)
        self.assertEqual(
                str(Path(lak.LakContext.DEFAULT_PORTFOLIO).expanduser()),
                lakctx.portfolio_filename)
        MockCache.set_cache_dir.assert_not_called()

    @patch('lakshmi.lak.LakContext._ReturnConfig')
    @patch('lakshmi.cache')
    @patch('pathlib.Path.exists')
    def testLakContextInitFileNotFound(
            self, MockExists, MockCache, MockReturnConfig):
        MockReturnConfig.return_value = {
            'portfolio': 'portfolio.yaml'}
        MockExists.return_value = False

        # This shouldn't raise an exception until the portfolio
        # is actually loaded.
        lakctx = lak.LakContext()

        with self.assertRaisesRegex(
                click.ClickException,
                'Portfolio file portfolio.yaml does not'):
            lakctx.Portfolio()

        MockCache.set_cache_dir.assert_not_called()
        MockExists.assert_called_with()

    def testListTotal(self):
        result = RunLak('list -f plain total')
        self.assertEqual(0, result.exit_code)
        self.assertIn('Total Assets  $100.00', result.output)
        self.assertNotIn('\n\n', result.output)
        self.assertFalse(lak.lakctx.saved)

    def testListWithChaining(self):
        result = RunLak('list al total')
        self.assertEqual(0, result.exit_code)
        # Test that the separater was printed.
        self.assertIn('\n\n', result.output)
        self.assertFalse(lak.lakctx.saved)

    def testListAANoArgs(self):
        result = RunLak('list aa')
        self.assertEqual(0, result.exit_code)
        # Check if compact version was printed.
        self.assertRegex(result.output, 'Class +A% +D%')
        self.assertFalse(lak.lakctx.saved)

    def testListAANoCompact(self):
        result = RunLak('list aa --no-compact')
        self.assertEqual(0, result.exit_code)
        # Check if tree version was printed.
        self.assertRegex(result.output, 'Class +Actual% .+Value\n')
        self.assertFalse(lak.lakctx.saved)

    def testListAAClassWithBadArgs(self):
        result = RunLak('list aa --no-compact --asset-class a,b,c')
        self.assertEqual(2, result.exit_code)
        self.assertTrue('is only supported' in result.output)
        self.assertFalse(lak.lakctx.saved)

    def testListAAClass(self):
        result = RunLak('list aa --asset-class Stocks,Bonds')
        self.assertEqual(0, result.exit_code)
        # Check if correct version was printed.
        self.assertRegex(result.output, 'Class +Actual% .+Difference\n')
        self.assertFalse(lak.lakctx.saved)

    def testListAssets(self):
        result = RunLak('list assets')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Account +Asset +Value\n')
        self.assertFalse(lak.lakctx.saved)

    def testListWhatIfsEmpty(self):
        result = RunLak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertFalse(lak.lakctx.saved)

    def testWhatIf(self):
        result = RunLak('whatif asset -a Test -100')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertTrue(lak.lakctx.saved)
        lak.lakctx.Reset()

        result = RunLak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Account +Cash\n')
        self.assertRegex(result.output, 'Account +Asset +Delta\n')
        self.assertFalse(lak.lakctx.saved)
        lak.lakctx.Reset()

        result = RunLak('list assets')
        self.assertEqual(0, result.exit_code)
        self.assertIn('Hypothetical what ifs', result.output)
        self.assertFalse(lak.lakctx.saved)
        lak.lakctx.Reset()

        result = RunLak('whatif --reset')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertTrue(lak.lakctx.saved)
        lak.lakctx.Reset()

        result = RunLak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertFalse(lak.lakctx.saved)

    def testWhatIfAccount(self):
        result = RunLak('whatif account -t Schwab -100')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertTrue(lak.lakctx.saved)
        lak.lakctx.Reset()

        result = RunLak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Account +Cash\n')
        self.assertNotRegex(result.output, 'Account +Asset +Delta\n')
        self.assertFalse(lak.lakctx.saved)
        lak.lakctx.Reset()

    def testInfoAccount(self):
        result = RunLak('info account -t Schwab')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Name: +Schwab\n')
        self.assertFalse(lak.lakctx.saved)

    def testInfoAsset(self):
        result = RunLak('info asset -a Test')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Name: +Test Asset\n')
        self.assertFalse(lak.lakctx.saved)

    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def testEditAndParseWithNoDict(self, mock_read_text, mock_edit):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = 'c: d'

        actual = lak.EditAndParse(None, lambda x: x, 'test_file')

        self.assertEqual({'c' : 'd'}, actual)
        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('a: b')

    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def testEditAndParseWithDict(self, mock_read_text, mock_edit):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = 'c: d\n\n' + lak._HELP_MSG_PREFIX

        actual = lak.EditAndParse({'e': 'f'}, lambda x: x, 'test_file')

        self.assertEqual({'c': 'd'}, actual)
        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('e: f\n' + lak._HELP_MSG_PREFIX + '# a: b')

    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def testEditAndParseAborted(self, mock_read_text, mock_edit):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = None

        with self.assertRaises(click.Abort):
            lak.EditAndParse(None, lambda x: x, 'test_file')

        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('a: b')

    @patch('click.echo')
    @patch('click.confirm')
    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def testEditAndParseUserAborted(self, mock_read_text, mock_edit,
            mock_confirm, mock_echo):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = 'c: d'
        mock_confirm.return_value = False

        def ParseFn(x):
            raise Exception('Better luck next time')

        with self.assertRaises(click.Abort):
            actual = lak.EditAndParse(None, ParseFn, 'test_file')

        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('a: b')
        mock_confirm.assert_called_once()
        mock_echo.assert_called_with('Error parsing file: '
                                      "Exception('Better luck next time')")

    @patch('click.echo')
    @patch('click.confirm')
    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def testEditAndParseUserFixed(self, mock_read_text, mock_edit,
            mock_confirm, mock_echo):
        mock_read_text.return_value = 'a: b'
        mock_edit.side_effect = ['c~~d', 'c: d']
        mock_confirm.return_value = True

        def ParseFn(x):
            if x == 'c~~d':
                raise Exception('Better luck next time')
            else:
                return x

        actual = lak.EditAndParse(None, ParseFn, 'test_file')
        self.assertEqual({'c': 'd'}, actual)

        mock_read_text.assert_called_once()
        mock_edit.assert_has_calls([unittest.mock.call('a: b'),
                                    unittest.mock.call('c~~d')])
        mock_confirm.assert_called_once()
        mock_echo.assert_called_with('Error parsing file: '
                                      "Exception('Better luck next time')")

    @patch('pathlib.Path.exists')
    def testInitPortfolioExists(self, mock_exists):
        mock_exists.return_value = True

        result = RunLak('init')
        self.assertEqual(1, result.exit_code)
        self.assertIn('Portfolio file already', result.output)
        self.assertFalse(lak.lakctx.saved)

    @patch('lakshmi.lak.EditAndParse')
    @patch('pathlib.Path.exists')
    def testInitPortfolio(self, mock_exists, MockParse):
        mock_exists.return_value = False
        MockParse.return_value = AssetClass('Money')

        result = RunLak('init')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual('Money', lak.lakctx.portfolio.asset_classes.name)

    @patch('lakshmi.lak.EditAndParse')
    def testEditAssetClass(self, MockParse):
        MockParse.return_value = AssetClass('Money')

        previous_ac_dict = lak.lakctx.portfolio.asset_classes.ToDict()
        result = RunLak('edit assetclass')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual('Money', lak.lakctx.portfolio.asset_classes.name)

        MockParse.assert_called_with(previous_ac_dict,
                                     unittest.mock.ANY,
                                     'AssetClass.yaml')

    def testEditAccountBadName(self):
        result = RunLak('edit account -t Yolo')
        self.assertEqual(1, result.exit_code)
        self.assertFalse(lak.lakctx.saved)

    @patch('lakshmi.lak.EditAndParse')
    def testEditAccountChangeType(self, MockParse):
        MockParse.return_value = Account('Schwab', 'Tax-exempt')

        result = RunLak('edit account -t Schwab')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        accounts = list(lak.lakctx.portfolio.Accounts())
        self.assertEqual(1, len(accounts))
        self.assertEqual('Tax-exempt', accounts[0].account_type)
        self.assertEqual(1, len(accounts[0].Assets()))

        MockParse.assert_called_with(Account('Schwab', 'Taxable').ToDict(),
                                     unittest.mock.ANY,
                                     'Account.yaml')

    @patch('lakshmi.lak.EditAndParse')
    def testEditAccountChangeName(self, MockParse):
        MockParse.return_value = Account('Vanguard', 'Taxable')

        result = RunLak('edit account -t Schwab')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        accounts = list(lak.lakctx.portfolio.Accounts())
        self.assertEqual(1, len(accounts))
        self.assertEqual('Vanguard', accounts[0].Name())
        self.assertEqual(1, len(accounts[0].Assets()))

        MockParse.assert_called_with(Account('Schwab', 'Taxable').ToDict(),
                                     unittest.mock.ANY,
                                     'Account.yaml')

    @patch('lakshmi.lak.EditAndParse')
    def testEditAsset(self, MockParse):
        MockParse.return_value = ManualAsset(
            'Tasty Asset', 100.0, {'Stocks' : 1.0})

        result = RunLak('edit asset -a Test')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        account = lak.lakctx.portfolio.GetAccount('Schwab')
        self.assertEqual(1, len(account.Assets()))
        self.assertEqual('Tasty Asset', list(account.Assets())[0].Name())

        MockParse.assert_called_with(
            ManualAsset('Test Asset', 100.0, {'Stocks': 1.0}).ToDict(),
            unittest.mock.ANY,
            'ManualAsset.yaml')

    @patch('lakshmi.lak.EditAndParse')
    def testAddAccount(self, MockParse):
        MockParse.return_value = Account('Vanguard', 'Taxable')

        result = RunLak('add account')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        self.assertEqual(2, len(lak.lakctx.portfolio.Accounts()))
        MockParse.assert_called_with(None,
                                     Account.FromDict,
                                     'Account.yaml')

    @patch('lakshmi.lak.EditAndParse')
    def testAddAsset(self, MockParse):
        MockParse.return_value = ManualAsset(
            'Tasty Asset', 100.0, {'Stocks' : 1.0})

        result = RunLak('add asset -t Schwab -p ManualAsset')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        account = lak.lakctx.portfolio.GetAccount('Schwab')
        self.assertEqual(2, len(account.Assets()))

        MockParse.assert_called_with(
            None,
            ManualAsset.FromDict,
            'ManualAsset.yaml')

    def testDeleteAccount(self):
        result = RunLak('delete account -t Schwab --yes')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual(0, len(lak.lakctx.portfolio.Accounts()))

    def testDeleteAsset(self):
        result = RunLak('delete asset -a Test --yes')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual(
            0, len(lak.lakctx.portfolio.GetAccount('Schwab').Assets()))

    def testAnalyzeTLH(self):
        result = RunLak('analyze tlh')
        self.assertEqual(0, result.exit_code)
        self.assertIn('No tax lots', result.output)

    def testAnalyzeRebalance(self):
        result = RunLak('analyze rebalance')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Bonds +0')


if __name__ == '__main__':
    unittest.main()
