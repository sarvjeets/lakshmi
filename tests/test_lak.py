"""Tests for lakshmi.lak application."""
import unittest
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner

from lakshmi import Account, AssetClass, Portfolio, lak
from lakshmi.assets import ManualAsset


class TestLakContext(lak.LakContext):
    """A testing version of LakContext that doesn't load or save
    portfolio."""

    def __init__(self):
        self.portfolio_filename = 'test_portfolio.yaml'
        self.continued = False
        self.warned = False
        self.whatifs = None
        self.tablefmt = None
        self.saved = False

        self.portfolio = Portfolio(
            AssetClass('All')
            .add_subclass(0.5, AssetClass('Stocks'))
            .add_subclass(0.5, AssetClass('Bonds'))).add_account(
            Account('Schwab', 'Taxable').add_asset(
                ManualAsset('Test Asset', 100.0, {'Stocks': 1.0})))

    def get_portfolio(self):
        return self.portfolio

    def save_portfolio(self):
        self.saved = True

    def reset(self):
        """Reset the state for a new command (except the portfolio)."""
        self.continued = False
        self.warned = False
        self.whatifs = None
        self.tablefmt = None
        self.saved = False


def run_lak(args):
    return CliRunner().invoke(lak.lak, args.split(' '))


class LakTest(unittest.TestCase):
    def setUp(self):
        lak.lakctx = TestLakContext()

    @patch('lakshmi.lak.LakContext._return_config')
    @patch('lakshmi.cache')
    @patch('pathlib.Path.exists')
    def test_lak_context_init_with_no_config(
            self, mock_exists, mock_cache, mock_return_config):
        mock_return_config.return_value = {}
        mock_exists.return_value = True

        lakctx = lak.LakContext()
        self.assertFalse(lakctx.continued)
        self.assertIsNone(lakctx.whatifs)
        self.assertIsNone(lakctx.portfolio)
        self.assertEqual(
            str(Path(lak.LakContext.DEFAULT_PORTFOLIO).expanduser()),
            lakctx.portfolio_filename)
        mock_cache.set_cache_dir.assert_not_called()

    @patch('lakshmi.lak.LakContext._return_config')
    @patch('lakshmi.cache')
    @patch('pathlib.Path.exists')
    def test_lak_context_init_file_not_found(
            self, mock_exists, mock_cache, mock_return_config):
        mock_return_config.return_value = {
            'portfolio': 'portfolio.yaml'}
        mock_exists.return_value = False

        # This shouldn't raise an exception until the portfolio
        # is actually loaded.
        lakctx = lak.LakContext()

        with self.assertRaisesRegex(
                click.ClickException,
                'Portfolio file portfolio.yaml does not'):
            lakctx.get_portfolio()

        mock_cache.set_cache_dir.assert_not_called()
        mock_exists.assert_called_with()

    def test_list_total(self):
        result = run_lak('list -f plain total')
        self.assertEqual(0, result.exit_code)
        self.assertIn('Total Assets  $100.00', result.output)
        self.assertNotIn('\n\n', result.output)
        self.assertFalse(lak.lakctx.saved)

    def test_list_with_chaining(self):
        result = run_lak('list al total')
        self.assertEqual(0, result.exit_code)
        # Test that the separater was printed.
        self.assertIn('\n\n', result.output)
        self.assertFalse(lak.lakctx.saved)

    def test_list_aa_no_args(self):
        result = run_lak('list aa')
        self.assertEqual(0, result.exit_code)
        # Check if compact version was printed.
        self.assertRegex(result.output, 'Class +A% +D%')
        self.assertFalse(lak.lakctx.saved)

    def test_list_aa_no_compact(self):
        result = run_lak('list aa --no-compact')
        self.assertEqual(0, result.exit_code)
        # Check if tree version was printed.
        self.assertRegex(result.output, 'Class +Actual% .+Value\n')
        self.assertFalse(lak.lakctx.saved)

    def test_list_aa_class_with_bad_args(self):
        result = run_lak('list aa --no-compact --asset-class a,b,c')
        self.assertEqual(2, result.exit_code)
        self.assertTrue('is only supported' in result.output)
        self.assertFalse(lak.lakctx.saved)

    def test_list_aa_class(self):
        result = run_lak('list aa --asset-class Stocks,Bonds')
        self.assertEqual(0, result.exit_code)
        # Check if correct version was printed.
        self.assertRegex(result.output, 'Class +Actual% .+Difference\n')
        self.assertFalse(lak.lakctx.saved)

    def test_list_assets(self):
        result = run_lak('list assets')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Account +Asset +Value\n')
        self.assertFalse(lak.lakctx.saved)

    def test_list_lots(self):
        result = run_lak('list lots')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertFalse(lak.lakctx.saved)

    def test_list_what_ifs_empty(self):
        result = run_lak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertFalse(lak.lakctx.saved)

    def test_what_if(self):
        result = run_lak('whatif asset -a Test -100')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertTrue(lak.lakctx.saved)
        lak.lakctx.reset()

        result = run_lak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Account +Cash\n')
        self.assertRegex(result.output, 'Account +Asset +Delta\n')
        self.assertFalse(lak.lakctx.saved)
        lak.lakctx.reset()

        result = run_lak('list assets')
        self.assertEqual(0, result.exit_code)
        self.assertIn('Hypothetical what ifs', result.output)
        self.assertFalse(lak.lakctx.saved)
        lak.lakctx.reset()

        result = run_lak('whatif --reset')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertTrue(lak.lakctx.saved)
        lak.lakctx.reset()

        result = run_lak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertFalse(lak.lakctx.saved)

    def test_what_if_account(self):
        result = run_lak('whatif account -t Schwab -100')
        self.assertEqual(0, result.exit_code)
        self.assertEqual('', result.output)
        self.assertTrue(lak.lakctx.saved)
        lak.lakctx.reset()

        result = run_lak('list whatifs')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Account +Cash\n')
        self.assertNotRegex(result.output, 'Account +Asset +Delta\n')
        self.assertFalse(lak.lakctx.saved)
        lak.lakctx.reset()

    def test_info_account(self):
        result = run_lak('info account -t Schwab')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Name: +Schwab\n')
        self.assertFalse(lak.lakctx.saved)

    def test_info_asset(self):
        result = run_lak('info asset -a Test')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Name: +Test Asset\n')
        self.assertFalse(lak.lakctx.saved)

    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def test_edit_and_parse_with_no_dict(self, mock_read_text, mock_edit):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = 'c: d'

        actual = lak.edit_and_parse(None, lambda x: x, 'test_file')

        self.assertEqual({'c': 'd'}, actual)
        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('a: b')

    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def test_edit_and_parse_with_dict(self, mock_read_text, mock_edit):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = 'c: d\n\n' + lak._HELP_MSG_PREFIX

        actual = lak.edit_and_parse({'e': 'f'}, lambda x: x, 'test_file')

        self.assertEqual({'c': 'd'}, actual)
        mock_read_text.assert_called_once()
        mock_edit.assert_called_with(
            'e: f\n' + lak._HELP_MSG_PREFIX + '# a: b')

    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def test_edit_and_parse_aborted(self, mock_read_text, mock_edit):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = None

        with self.assertRaises(click.Abort):
            lak.edit_and_parse(None, lambda x: x, 'test_file')

        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('a: b')

    @patch('click.echo')
    @patch('click.confirm')
    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def test_edit_and_parse_user_aborted(self, mock_read_text, mock_edit,
                                         mock_confirm, mock_echo):
        mock_read_text.return_value = 'a: b'
        mock_edit.return_value = 'c: d'
        mock_confirm.return_value = False

        def parse_fn(x):
            raise Exception('Better luck next time')

        with self.assertRaises(click.Abort):
            lak.edit_and_parse(None, parse_fn, 'test_file')

        mock_read_text.assert_called_once()
        mock_edit.assert_called_with('a: b')
        mock_confirm.assert_called_once()
        mock_echo.assert_called_with('Error parsing file: '
                                     "Exception('Better luck next time')")

    @patch('click.echo')
    @patch('click.confirm')
    @patch('click.edit')
    @patch('pathlib.Path.read_text')
    def test_edit_and_parse_user_fixed(self, mock_read_text, mock_edit,
                                       mock_confirm, mock_echo):
        mock_read_text.return_value = 'a: b'
        mock_edit.side_effect = ['c~~d', 'c: d']
        mock_confirm.return_value = True

        def parse_fn(x):
            if x == 'c~~d':
                raise Exception('Better luck next time')
            else:
                return x

        actual = lak.edit_and_parse(None, parse_fn, 'test_file')
        self.assertEqual({'c': 'd'}, actual)

        mock_read_text.assert_called_once()
        mock_edit.assert_has_calls([unittest.mock.call('a: b'),
                                    unittest.mock.call('c~~d')])
        mock_confirm.assert_called_once()
        mock_echo.assert_called_with('Error parsing file: '
                                     "Exception('Better luck next time')")

    @patch('pathlib.Path.exists')
    def test_init_portfolio_exists(self, mock_exists):
        mock_exists.return_value = True

        result = run_lak('init')
        self.assertEqual(1, result.exit_code)
        self.assertIn('Portfolio file already', result.output)
        self.assertFalse(lak.lakctx.saved)

    @patch('lakshmi.lak.edit_and_parse')
    @patch('pathlib.Path.exists')
    def test_init_portfolio(self, mock_exists, mock_parse):
        mock_exists.return_value = False
        mock_parse.return_value = AssetClass('Money')

        result = run_lak('init')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual('Money', lak.lakctx.portfolio.asset_classes.name)

    @patch('lakshmi.lak.edit_and_parse')
    def test_edit_asset_class(self, mock_parse):
        mock_parse.return_value = AssetClass('Money')

        previous_ac_dict = lak.lakctx.portfolio.asset_classes.to_dict()
        result = run_lak('edit assetclass')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual('Money', lak.lakctx.portfolio.asset_classes.name)

        mock_parse.assert_called_with(previous_ac_dict,
                                      unittest.mock.ANY,
                                      'AssetClass.yaml')

    def test_edit_account_bad_name(self):
        result = run_lak('edit account -t Yolo')
        self.assertEqual(1, result.exit_code)
        self.assertFalse(lak.lakctx.saved)

    @patch('lakshmi.lak.edit_and_parse')
    def test_edit_account_change_type(self, mock_parse):
        mock_parse.return_value = Account('Schwab', 'Tax-exempt')

        result = run_lak('edit account -t Schwab')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        accounts = list(lak.lakctx.portfolio.accounts())
        self.assertEqual(1, len(accounts))
        self.assertEqual('Tax-exempt', accounts[0].account_type)
        self.assertEqual(1, len(accounts[0].assets()))

        mock_parse.assert_called_with(Account('Schwab', 'Taxable').to_dict(),
                                      unittest.mock.ANY,
                                      'Account.yaml')

    @patch('lakshmi.lak.edit_and_parse')
    def test_edit_account_change_name(self, mock_parse):
        mock_parse.return_value = Account('Vanguard', 'Taxable')

        result = run_lak('edit account -t Schwab')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        accounts = list(lak.lakctx.portfolio.accounts())
        self.assertEqual(1, len(accounts))
        self.assertEqual('Vanguard', accounts[0].name())
        self.assertEqual(1, len(accounts[0].assets()))

        mock_parse.assert_called_with(Account('Schwab', 'Taxable').to_dict(),
                                      unittest.mock.ANY,
                                      'Account.yaml')

    @patch('lakshmi.lak.edit_and_parse')
    def test_edit_asset(self, mock_parse):
        mock_parse.return_value = ManualAsset(
            'Tasty Asset', 100.0, {'Stocks': 1.0})

        result = run_lak('edit asset -a Test')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        account = lak.lakctx.portfolio.get_account('Schwab')
        self.assertEqual(1, len(account.assets()))
        self.assertEqual('Tasty Asset', list(account.assets())[0].name())

        mock_parse.assert_called_with(
            ManualAsset('Test Asset', 100.0, {'Stocks': 1.0}).to_dict(),
            unittest.mock.ANY,
            'ManualAsset.yaml')

    @patch('lakshmi.lak.edit_and_parse')
    def test_add_account(self, mock_parse):
        mock_parse.return_value = Account('Vanguard', 'Taxable')

        result = run_lak('add account')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        self.assertEqual(2, len(lak.lakctx.portfolio.accounts()))
        mock_parse.assert_called_with(None,
                                      Account.from_dict,
                                      'Account.yaml')

    @patch('lakshmi.lak.edit_and_parse')
    def test_add_asset(self, mock_parse):
        mock_parse.return_value = ManualAsset(
            'Tasty Asset', 100.0, {'Stocks': 1.0})

        result = run_lak('add asset -t Schwab -p ManualAsset')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)

        account = lak.lakctx.portfolio.get_account('Schwab')
        self.assertEqual(2, len(account.assets()))

        mock_parse.assert_called_with(
            None,
            ManualAsset.from_dict,
            'ManualAsset.yaml')

    def test_delete_account(self):
        result = run_lak('delete account -t Schwab --yes')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual(0, len(lak.lakctx.portfolio.accounts()))

    def test_delete_asset(self):
        result = run_lak('delete asset -a Test --yes')
        self.assertEqual(0, result.exit_code)
        self.assertTrue(lak.lakctx.saved)
        self.assertEqual(
            0, len(lak.lakctx.portfolio.get_account('Schwab').assets()))

    def test_analyze_tlh(self):
        result = run_lak('analyze tlh')
        self.assertEqual(0, result.exit_code)
        self.assertIn('No tax lots', result.output)

    def test_analyze_rebalance(self):
        result = run_lak('analyze rebalance')
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, 'Bonds +0')


if __name__ == '__main__':
    unittest.main()
