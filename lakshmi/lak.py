"""Command line interface for Lakshmi.

This is meant to be used as an application and would not work well if used
as library (by design it keeps a lot of global state and is not safe to be
called multiple times from the same program). If there is ever need to use
it as a library, this code requires major refactoring to clean it up."""

from pathlib import Path

import click
import yaml

import lakshmi.analyze
import lakshmi.assets
import lakshmi.cache
from lakshmi import Portfolio
from lakshmi.table import Table


class LakContext:
    """Context class with utilities to help the script keep state and
    share it."""
    DEFAULT_PORTFOLIO = '~/portfolio.yaml'

    def _return_config(self):
        """Internal function to read and return .lakrc file."""
        lakrcfile = Path(self.lakrc).expanduser()

        if not lakrcfile.exists():
            return {}
        config = yaml.load(lakrcfile.read_text(), Loader=yaml.SafeLoader)
        return config

    def __init__(self, lakrc='~/.lakrc'):
        self.lakrc = lakrc
        # Used in self.optional_separator()
        self.continued = False
        # Used in self.warn_for_what_ifs()
        self.warned = False
        # List of hypothetical whatifs. Used in self.get_what_ifs() and
        # self.warn_for_what_ifs()
        self.whatifs = None
        # The loaded portfolio.
        self.portfolio = None
        self.tablefmt = None

        config = self._return_config()

        portfolio_filename = config.pop(
            'portfolio', LakContext.DEFAULT_PORTFOLIO)
        self.portfolio_filename = str(Path(portfolio_filename).expanduser())

        # Setup cache directory.
        if 'cache' in config:
            cache_dir = config.pop('cache')
            if cache_dir is None:
                # Disable caching.
                lakshmi.cache.set_cache_dir(None)
            else:
                lakshmi.cache.set_cache_dir(Path(cache_dir).expanduser())

        if len(config):
            raise click.ClickException('Extra entries found in config file: '
                                       f'{list(config.keys())}')

    def optional_separator(self):
        """Prints a newline between multiple commands. Used to add a newline
        between cmd1, cmd2, cmd3, etc. in 'lak list cmd1 cmd2 cmd3'."""
        # Don't print separator if this is the first time we are called.
        if self.continued:
            click.echo()
        # Set it up so that separator is printed for the next command.
        self.continued = True

    def get_what_ifs(self):
        """Load and return a list of hypothetical whatifs in the portfolio."""
        if not self.whatifs:
            self.whatifs = self.get_portfolio().get_what_ifs()
        return self.whatifs

    def warn_for_what_ifs(self):
        """Prints a warning if whatifs are set."""
        # Make sure we don't print warning multiple times if commands are
        # chained.
        if self.warned:
            return
        self.get_what_ifs()
        if self.whatifs[0].list() or self.whatifs[1].list():
            click.secho('Warning: Hypothetical what ifs are set.\n', fg='red')
        self.warned = True

    def get_portfolio(self):
        """Loads and returns the portfolio from self.portfolio_filename."""
        if not self.portfolio:
            # Check if portfolio file doesn't exist and print helpful error
            # message.
            portfolio_file = Path(self.portfolio_filename).expanduser()
            if not portfolio_file.exists():
                raise click.ClickException(
                    f'Portfolio file {portfolio_file} does not exist. Please '
                    'use "lak init" to create a new portfolio.')

            self.portfolio = Portfolio.load(self.portfolio_filename)
        return self.portfolio

    def save_portfolio(self):
        """Save self.portfolio back to file."""
        self.portfolio.save(self.portfolio_filename)


# Global variable to save and pass context between click commands.
#
# I tried using click's builtin context, but it was too troublesome
# and didn't exactly give us the functionality that I wanted
# -- sarvjeets
lakctx = None


class Spinner:
    """Prints a progress bar on the screen for cache misses."""
    SPINNER = ('▰▱▱▱▱▱▱',
               '▰▰▱▱▱▱▱',
               '▰▰▰▱▱▱▱',
               '▰▰▰▰▱▱▱',
               '▰▰▰▰▰▱▱',
               '▰▰▰▰▰▰▱',
               '▰▰▰▰▰▰▰')

    def __init__(self):
        self._index = 0  # Index within _SPINNER
        self._spinning = False  # Set to true once we start 'spinning'
        self._isatty = True  # Are we connected to tty?
        try:
            self._isatty = click.get_binary_stream('stdout').isatty()
        except Exception:
            self._isatty = False

    def __enter__(self):
        if not self._isatty:  # Not on terminal, do nothing.
            return

        def spin():
            if self._spinning:
                click.echo('\b' * len(Spinner.SPINNER[0]), nl=False)
            else:
                self._spinning = True

            click.echo(Spinner.SPINNER[self._index], nl=False)
            self._index = (self._index + 1) % len(Spinner.SPINNER)

        # Setup so that cache calls spin
        lakshmi.cache.set_cache_miss_func(spin)
        return spin

    def __exit__(self, *args):
        lakshmi.cache.set_cache_miss_func(None)  # Disable spinner
        if self._spinning:
            click.echo('\b' * len(Spinner.SPINNER[0]), nl=False)


@click.group()
@click.version_option()
@click.option('--refresh', '-r', is_flag=True,
              help='Re-fetch all data instead of using previously cached '
              'data. For large portfolios, this would be extremely slow.')
def lak(refresh):
    """lak is a simple command line tool inspired by Bogleheads philosophy.
    Detailed user guide is available at:
    https://sarvjeets.github.io/lakshmi/docs/lak.html"""
    lakshmi.cache.set_force_refresh(refresh)
    global lakctx
    if not lakctx:
        # Setup a new context object for child commands.
        lakctx = LakContext()


@lak.group(chain=True)
@click.option('--format', '-f',
              type=click.Choice(
                  ['plain', 'simple', 'github', 'grid', 'fancy_grid',
                   'pipe', 'orgtbl', 'rst', 'mediawiki', 'html', 'latex',
                   'latex_raw', 'latex_booktabs', 'latex_longtable', 'tsv'],
                  case_sensitive=False),
              default='simple',
              help='Set output table format. For more information on table '
              'formats, please see "Table format" section on: '
              'https://pypi.org/project/tabulate/')
def list(format):
    """Command to list various parts of the portfolio."""
    global lakctx
    lakctx.tablefmt = format


@list.command()
def total():
    """Prints the total value of the portfolio."""
    global lakctx
    lakctx.optional_separator()
    lakctx.warn_for_what_ifs()
    portfolio = lakctx.get_portfolio()

    with Spinner():
        output = Table(2, coltypes=['str', 'dollars']).add_row(
            ['Total Assets', portfolio.total_value()]).string(lakctx.tablefmt)
    click.echo(output)


@list.command()
def al():
    """Prints the Asset Location of the portfolio. For more information,
    please see
    https://www.bogleheads.org/wiki/Tax-efficient_fund_placement"""
    global lakctx
    lakctx.optional_separator()
    lakctx.warn_for_what_ifs()
    portfolio = lakctx.get_portfolio()
    with Spinner():
        output = portfolio.asset_location().string(lakctx.tablefmt)
    click.echo(output)


@list.command()
@click.option('--compact/--no-compact', default=True, show_default=True,
              help='Print the Asset allocation tree in a vertically '
              'compact format')
@click.option('--asset-class', '-c', type=str,
              help='If provided, only print asset allocation for these asset '
              'classes. This is a comma separated list of asset classes (not '
              'necessarily leaf asset classes) and the allocation across '
              'these asset classes should sum to 100%.')
def aa(compact, asset_class):
    """Prints the Asset Allocation of the portfolio. For more information,
    please see https://www.bogleheads.org/wiki/Asset_allocation"""
    global lakctx
    lakctx.optional_separator()
    lakctx.warn_for_what_ifs()

    portfolio = lakctx.get_portfolio()
    with Spinner():
        if asset_class:
            if not compact:
                raise click.UsageError(
                    '--no-compact is only supported when --asset-class '
                    'is not specified.')
            classes_list = [c.strip() for c in asset_class.split(',')]
            output = portfolio.asset_allocation(classes_list).string(
                lakctx.tablefmt)
        else:
            if compact:
                output = portfolio.asset_allocation_compact().string(
                    lakctx.tablefmt)
            else:
                output = portfolio.asset_allocation_tree().string(
                    lakctx.tablefmt)
    click.echo(output)


@list.command()
@click.option('--short-name', '-s', is_flag=True,
              help='Print the short name of the assets as well (e.g. Ticker '
              'for assets that have it).')
@click.option('--quantity', '-q', is_flag=True,
              help='Print the quantity of the asset (e.g. quantity/shares '
              'for assets that have it).')
def assets(short_name, quantity):
    """Prints all assets in the portfolio and their current values."""
    global lakctx
    lakctx.optional_separator()
    lakctx.warn_for_what_ifs()
    portfolio = lakctx.get_portfolio()
    with Spinner():
        output = portfolio.assets(
            short_name=short_name, quantity=quantity).string(lakctx.tablefmt)
    click.echo(output)


@list.command()
def whatifs():
    """Prints hypothetical what ifs for assets and accounts."""
    global lakctx
    account_whatifs, asset_whatifs = lakctx.get_what_ifs()
    if account_whatifs.list():
        lakctx.optional_separator()
        click.echo(account_whatifs.string(lakctx.tablefmt))
    if asset_whatifs.list():
        lakctx.optional_separator()
        click.echo(asset_whatifs.string(lakctx.tablefmt))
    lakctx.warned = True  # Don't warn about whatifs if command is chained.


@list.command()
def lots():
    """Prints tax lot information for all the assets."""
    global lakctx
    lakctx.optional_separator()
    with Spinner():
        output = lakctx.get_portfolio().list_lots().string(lakctx.tablefmt)
    if output:
        click.echo(output)


@lak.group(chain=True,
           invoke_without_command=True)
@click.option('--reset', '-r', is_flag=True,
              help='Reset all hypothetical whatif amounts.')
def whatif(reset):
    """Run hypothetical what if scenarios by modifying the total value of
    an account or asset. This is useful to see how the asset allocation
    or location will change if you make these changes. Once you are done
    playing around with the hypothetical changes, you can reset them all
    by using the --reset flag."""
    if reset:
        global lakctx
        lakctx.get_portfolio().reset_what_ifs()
        lakctx.save_portfolio()


# ignore_unknown_options is there to make sure -100 is parsed as delta
# and click doesn't think it is an option.
@whatif.command(context_settings={"ignore_unknown_options": True})
@click.option('--account', '-t', type=str, metavar='substr', required=True,
              help='Change the value of account that matches this substring')
@click.argument('delta', type=float, required=True)
def account(account, delta):
    """Run hypothetical what if scenario on an account.
    This command adds DELTA to the value of account specified."""
    global lakctx
    portfolio = lakctx.get_portfolio()
    account_name = portfolio.get_account_name_by_substr(account)
    portfolio.what_if_add_cash(account_name, delta)
    lakctx.save_portfolio()


# ignore_unknown_options is there to make sure -100 is parsed as delta
# and click doesn't think it is an option.
@whatif.command(context_settings={"ignore_unknown_options": True})
@click.option('--asset', '-a', type=str, metavar='substr', required=True,
              help='Change the value of asset that matches this substring')
@click.option('--account', '-t', type=str, metavar='substr',
              help='If the asset name is not unique across the portfolio, '
              'an optional substring to specify the account to which the '
              'asset belongs.')
@click.argument('delta', type=float, required=True)
def asset(asset, account, delta):
    """Run hypothetical what if scenario on an asset.
    This command adds DELTA to the value of the asset specified."""
    global lakctx
    portfolio = lakctx.get_portfolio()
    account_name, asset_name = portfolio.get_asset_name_by_substr(
        account if account is not None else '', asset)
    portfolio.what_if(account_name, asset_name, delta)
    lakctx.save_portfolio()


@lak.group(chain=True)
def info():
    """Print detailed information about an asset or account."""
    pass


@info.command()
@click.option('--account', '-t', type=str, metavar='substr', required=True,
              help='Print info about the account that matches this substring')
def account(account):
    """Print details of an account."""
    global lakctx
    lakctx.optional_separator()

    portfolio = lakctx.get_portfolio()
    account_name = portfolio.get_account_name_by_substr(account)
    click.echo(portfolio.get_account(account_name).string())


@info.command()
@click.option('--asset', '-a', type=str, metavar='substr', required=True,
              help='Print info about the asset that matches this substring')
@click.option('--account', '-t', type=str, metavar='substr',
              help='If the asset name is not unique across the portfolio, '
              'an optional substring to specify the account to which the '
              'asset belongs.')
def asset(asset, account):
    """Print details of an asset."""
    global lakctx
    lakctx.optional_separator()

    portfolio = lakctx.get_portfolio()
    account_name, asset_name = portfolio.get_asset_name_by_substr(
        account if account is not None else '', asset)
    click.echo(portfolio.get_account(
        account_name).get_asset(asset_name).string())


@lak.group()
def edit():
    """Edit parts of the portfolio."""
    pass


_HELP_MSG_PREFIX = ('\n\n# # Lines starting with "#" are ignored and an '
                    'empty message aborts this command.\n\n')


def edit_and_parse(edit_dict, parse_fn, filename):
    """Helper funtion to edit parts of portfolio.

    This function is used to add/edit parts of the portfolio. It converts
    a dictionary representation of the object into a YAML file that the
    user can edit. The file is then converted back to a dictionary, which
    is parsed via the parse_fn to convert it into an object.

    Arguments:
        edit_dict: Dictionary representing an object that is being
        editted. This is usually the output of to_dict() of an object.
        parse_fn: The function used to parse the resulting dict generated
        by parsing the yaml file.
        filename: The file containing a template YAML file for the object
        being editted (inside lakshmi/data directory). If edit_dict is
        empty, this file is presented to the user so that the user can make
        changes inline. If edit_dict is set, this file is added as a
        comment at the end of the edit_dict representation as a helpful
        guide for the user.
    """
    # Change filename to absolute path.
    filepath = Path(__file__).resolve().parent / 'data' / filename
    if edit_dict:
        help_msg = _HELP_MSG_PREFIX + '# ' + filepath.read_text().replace(
            '\n', '\n# ')
        edit_str = yaml.dump(edit_dict, sort_keys=False) + help_msg
    else:
        edit_str = filepath.read_text()

    while True:
        edit_str = click.edit(edit_str)
        if not edit_str:  # No changes or empty string.
            raise click.Abort()
        try:
            parse_str = (edit_str.split(help_msg, 1)[0].rstrip('\n')
                         if edit_dict else edit_str)
            return parse_fn(yaml.load(parse_str, Loader=yaml.SafeLoader))
        except Exception as e:
            click.echo('Error parsing file: ' + repr(e))
            if not click.confirm('Do you want to edit again?'):
                raise click.Abort()


@lak.command()
def init():
    """Initializes a new portfolio by adding asset classes. This command can
    be used to create an empty portfolio file if one doesn't exist."""
    global lakctx
    if Path(lakctx.portfolio_filename).exists():
        raise click.ClickException(
            f'Portfolio file already exists: {lakctx.portfolio_filename}')

    asset_class = edit_and_parse(
        None,
        lambda x: lakshmi.AssetClass.from_dict(x).validate(),
        'AssetClass.yaml')
    lakctx.portfolio = Portfolio(asset_class)
    lakctx.save_portfolio()


@edit.command()
def assetclass():
    """Edit the Asset classes and the desired asset allocation."""
    global lakctx
    portfolio = lakctx.get_portfolio()

    asset_classes = edit_and_parse(
        portfolio.asset_classes.to_dict(),
        lambda x: lakshmi.AssetClass.from_dict(x).validate(),
        'AssetClass.yaml')
    portfolio.asset_classes = asset_classes
    lakctx.save_portfolio()


@edit.command()
@click.option('--account', '-t', type=str, metavar='substr', required=True,
              help='Edit the account that matches this substring')
def account(account):
    """Edit an account in the portfolio."""
    global lakctx
    portfolio = lakctx.get_portfolio()

    account_name = portfolio.get_account_name_by_substr(account)
    account_obj = portfolio.get_account(account_name)
    # Save assets and restore them after the user is done editing.
    assets = account_obj.assets()
    account_obj.set_assets([])

    account_obj = edit_and_parse(
        account_obj.to_dict(),
        lakshmi.Account.from_dict,
        'Account.yaml')
    account_obj.set_assets(assets)

    if account_obj.name() != account_name:
        portfolio.remove_account(account_name)
    portfolio.add_account(account_obj, replace=True)
    lakctx.save_portfolio()


@edit.command()
@click.option('--asset', '-a', type=str, metavar='substr', required=True,
              help='Edit the asset whose name or short name matches this '
              'substring.')
@click.option('--account', '-t', type=str, metavar='substr',
              help='If the asset name is not unique across the portfolio, '
              'an optional substring to specify the account to which the '
              'asset belongs.')
def asset(asset, account):
    """Edit an asset in the portfolio."""
    global lakctx
    portfolio = lakctx.get_portfolio()

    account_name, asset_name = portfolio.get_asset_name_by_substr(
        account if account is not None else '', asset)
    account_obj = portfolio.get_account(account_name)
    asset_obj = account_obj.get_asset(asset_name)

    asset_obj = edit_and_parse(asset_obj.to_dict(),
                               asset_obj.from_dict,
                               asset_obj.__class__.__name__ + '.yaml')

    if asset_obj.short_name() != asset_name:
        account_obj.remove_asset(asset_name)
    account_obj.add_asset(asset_obj, replace=True)

    lakctx.save_portfolio()


@lak.group()
def add():
    """Add new accounts or assets to the portfolio."""
    pass


@add.command()
def account():
    """Add a new account to the portfolio."""
    global lakctx
    portfolio = lakctx.get_portfolio()

    account = edit_and_parse(None, lakshmi.Account.from_dict, 'Account.yaml')
    portfolio.add_account(account)
    lakctx.save_portfolio()


@add.command()
@click.option('--asset-type', '-p', required=True,
              type=click.Choice([c.__name__ for c in lakshmi.assets.CLASSES],
                                case_sensitive=False),
              help='Add this type of asset.')
@click.option('--account', '-t', type=str, metavar='substr', required=True,
              help='Add asset to this account (a substring that matches the '
              'account name).')
def asset(asset_type, account):
    """Edit assets in the portfolio."""
    global lakctx
    portfolio = lakctx.get_portfolio()

    account_name = portfolio.get_account_name_by_substr(account)
    account_obj = portfolio.get_account(account_name)
    asset_cls = [
        c for c in lakshmi.assets.CLASSES if c.__name__ == asset_type][0]

    asset_obj = edit_and_parse(None, asset_cls.from_dict, asset_type + '.yaml')
    account_obj.add_asset(asset_obj)

    lakctx.save_portfolio()


@lak.group()
def delete():
    """Delete an account or asset."""
    pass


@delete.command()
@click.option('--account', '-t', type=str, metavar='substr', required=True,
              help='Delete the account that matches this substring')
@click.confirmation_option(prompt='This operation is not reversable. '
                           'Are you sure?')
def account(account):
    """Delete an account from the portfolio."""
    global lakctx
    portfolio = lakctx.get_portfolio()
    account_name = portfolio.get_account_name_by_substr(account)
    portfolio.remove_account(account_name)
    lakctx.save_portfolio()


@delete.command()
@click.option('--asset', '-a', type=str, metavar='substr', required=True,
              help='Delete the asset whose name or short name matches this '
              'substring.')
@click.option('--account', '-t', type=str, metavar='substr',
              help='If the asset name is not unique across the portfolio, '
              'optionally a substring to specify the account name '
              'from which the asset should be deleted.')
@click.confirmation_option(prompt='This operation is not reversable. '
                           'Are you sure?')
def asset(asset, account):
    """Delete an asset from the portfolio."""
    global lakctx
    portfolio = lakctx.get_portfolio()

    account_name, asset_name = portfolio.get_asset_name_by_substr(
        account if account is not None else '', asset)
    account_obj = portfolio.get_account(account_name)
    account_obj.remove_asset(asset_name)
    lakctx.save_portfolio()


@lak.group(chain=True)
def analyze():
    """Analyze the portfolio. """
    pass


@analyze.command()
@click.option('--max-percentage', '-p', type=float, default=10,
              show_default=True,
              help='The max percentage loss for each lot before TLHing.')
@click.option('--max-dollars', '-d', type=int,
              help='The max absolute loss for an asset (across all tax lots) '
              'before TLHing.')
def tlh(max_percentage, max_dollars):
    """Shows which tax lots can be Tax-loss harvested (TLH)."""
    global lakctx
    lakctx.optional_separator()
    with Spinner():
        table = lakshmi.analyze.TLH(max_percentage / 100, max_dollars).analyze(
            lakctx.get_portfolio())
    if not table.list():
        click.echo('No tax lots to harvest.')
    else:
        click.echo(table.string())


@analyze.command()
@click.option('--max-abs-percentage', '-a', type=float, default=5,
              show_default=True,
              help='Max absolute difference before rebalancing.')
@click.option('--max-relative-percentage', '-r', type=float, default=25,
              help='The max relative difference before rebalancing.')
def rebalance(max_abs_percentage, max_relative_percentage):
    """Shows if assets needs to be rebalanced based on a band
    based rebalancing scheme. For more information, please refer to
    https://www.whitecoatinvestor.com/rebalancing-the-525-rule/."""
    global lakctx
    lakctx.optional_separator()
    with Spinner():
        table = lakshmi.analyze.BandRebalance(
            max_abs_percentage / 100, max_relative_percentage / 100).analyze(
            lakctx.get_portfolio())
    if not table.list():
        click.echo('Portfolio Asset allocation within bounds.')
    else:
        click.echo(table.string())


if __name__ == '__main__':
    lak()
