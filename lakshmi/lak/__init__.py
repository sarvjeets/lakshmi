"""Command line interface for Lakshmi.

This is meant to be used as an application and would not work well if used
as library (by design it keeps a lot of global state and is not safe to be
called multiple times from the same program). If there is ever need to use
it as a library, this code requires major refactoring to clean it up."""

from pathlib import Path
from lakshmi import Portfolio
from lakshmi.table import Table
import click
import lakshmi.analyze
import lakshmi.assets
import lakshmi.cache
import yaml


class LakContext:
    """Context class with utilities to help the script keep state and
    share it."""
    DEFAULT_PORTFOLIO = '~/portfolio.yaml'

    def _ReturnConfig(self):
        """Internal function to read and return .lakrc file."""
        lakrcfile = Path(self.lakrc).expanduser()

        if not lakrcfile.exists():
            return {}
        config = yaml.load(lakrcfile.read_text(), Loader=yaml.SafeLoader)
        return config

    def __init__(self, lakrc='~/.lakrc'):
        self.lakrc = lakrc
        # Used in self.OptionalSeparator()
        self.continued = False
        # List of hypothetical whatifs. Used in self.GetWhatIfs() and
        # self.WarnForWhatIfs()
        self.whatifs = None
        # The loaded portfolio.
        self.portfolio = None
        self.tablefmt = None

        config = self._ReturnConfig()

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
            raise click.ClickException(f'Extra entries found in config file: '
                                       '{list(config.keys())}')

    def OptionalSeparator(self):
        """Prints a newline between multiple commands. Used to add a newline
        between cmd1, cmd2, cmd3, etc. in 'lak list cmd1 cmd2 cmd3'."""
        # Don't print separator if this is the first time we are called.
        if self.continued:
            click.echo()
        # Set it up so that separator is printed for the next command.
        self.continued = True

    def GetWhatIfs(self):
        """Load and return a list of hypothetical whatifs in the portfolio."""
        if not self.whatifs:
            self.whatifs = self.Portfolio().GetWhatIfs()
        return self.whatifs

    def WarnForWhatIfs(self):
        """Prints a warning if whatifs are set."""
        # Make sure we don't print warning multiple times if commands are
        # chained.
        if self.continued:
            return

        self.GetWhatIfs()
        if self.whatifs[0].List() or self.whatifs[1].List():
            click.secho('Warning: Hypothetical what ifs are set.\n', fg='red')

    def Portfolio(self):
        """Loads and returns the portfolio from self.portfolio_filename."""
        if not self.portfolio:
            # Check if portfolio file doesn't exist and print helpful error
            # message.
            portfolio_file = Path(self.portfolio_filename).expanduser()
            if not portfolio_file.exists():
                raise click.ClickException(
                    f'Portfolio file {portfolio_file} does not exist. Please '
                    'use "lak init" to create a new portfolio.')

            self.portfolio = Portfolio.Load(self.portfolio_filename)
        return self.portfolio

    def SavePortfolio(self):
        """Save self.portfolio back to file."""
        self.portfolio.Save(self.portfolio_filename)


# Global variable to save and pass context between click commands.
#
# I tried using click's builtin context, but it was too troublesome
# and didn't exactly give us the functionality that I wanted
# -- sarvjeets
lakctx = None


@click.group()
@click.version_option()
@click.option('--refresh', '-r', is_flag=True,
              help='Re-fetch all data instead of using previously cached '
              'data. For large portfolios this would be extremely slow.')
def lak(refresh):
    lakshmi.cache.set_force_refresh(refresh)
    global lakctx
    if not lakctx:
        # Setup a new context object for child commands.
        lakctx = LakContext()

@lak.group(chain=True)
@click.option('--format',  '-f',
              type=click.Choice(
                  ['plain', 'simple', 'github', 'grid', 'fancy_grid',
                    'pipe', 'orgtbl', 'rst', 'mediawiki', 'html', 'latex',
                    'latex_raw', 'latex_booktabs', 'latex_longtable', 'tsv'],
                  case_sensitive=False),
              default='simple',
              help='Set output table format. For more information on table'
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
    lakctx.WarnForWhatIfs()
    lakctx.OptionalSeparator()
    portfolio = lakctx.Portfolio()
    click.echo(
        Table(2, coltypes=['str', 'dollars']).AddRow(
            ['Total Assets', portfolio.TotalValue()]).String(lakctx.tablefmt))


@list.command()
def al():
    """Prints the Asset Location of the portfolio. For more information,
    please see
    https://www.bogleheads.org/wiki/Tax-efficient_fund_placement"""
    global lakctx
    lakctx.WarnForWhatIfs()
    lakctx.OptionalSeparator()
    portfolio = lakctx.Portfolio()
    click.echo(portfolio.AssetLocation().String(lakctx.tablefmt))


@list.command()
@click.option('--compact/--no-compact', default=True, show_default=True,
              help='Print the Asset allocation tree in a vertically '
              'compact format')
@click.option('--asset-class', '-a', type=str,
              help='If provided, only print asset allocation for these asset '
              'classes. This is comma seperated list of asset classes (not '
              'necessarily leaf asset classes) and the allocation across '
              'these asset classes should sum to 100%.')
def aa(compact, asset_class):
    """Prints the Asset Allocation of the portfolio. For more information,
    please see https://www.bogleheads.org/wiki/Asset_allocation"""
    global lakctx
    lakctx.WarnForWhatIfs()
    lakctx.OptionalSeparator()

    portfolio = lakctx.Portfolio()
    if asset_class:
        if not compact:
            raise click.UsageError(
                '--no-compact is only supported when --asset-class '
                'is not specified.')
        classes_list = [c.strip() for c in asset_class.split(',')]
        click.echo(portfolio.AssetAllocation(classes_list).String(
            lakctx.tablefmt))
    else:
        if compact:
            click.echo(portfolio.AssetAllocationCompact().String(
                lakctx.tablefmt))
        else:
            click.echo(portfolio.AssetAllocationTree().String(
                lakctx.tablefmt))


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
    lakctx.WarnForWhatIfs()
    lakctx.OptionalSeparator()
    portfolio = lakctx.Portfolio()
    click.echo(portfolio.Assets(short_name=short_name,
                                quantity=quantity).String(lakctx.tablefmt))


@list.command()
def whatifs():
    """Print hypothetical what ifs for assets and accounts."""
    global lakctx
    account_whatifs, asset_whatifs = lakctx.GetWhatIfs()
    if account_whatifs.List():
        lakctx.OptionalSeparator()
        click.echo(account_whatifs.String(lakctx.tablefmt))
    if asset_whatifs.List():
        lakctx.OptionalSeparator()
        click.echo(asset_whatifs.String(lakctx.tablefmt))


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
        lakctx.Portfolio().ResetWhatIfs()
        lakctx.SavePortfolio()


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
    portfolio = lakctx.Portfolio()
    account_name = portfolio.GetAccountNameBySubStr(account)
    portfolio.WhatIfAddCash(account_name, delta)
    lakctx.SavePortfolio()


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
    portfolio = lakctx.Portfolio()
    account_name, asset_name = portfolio.GetAssetNameBySubStr(
        account if account is not None else '', asset)
    portfolio.WhatIf(account_name, asset_name, delta)
    lakctx.SavePortfolio()


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
    lakctx.OptionalSeparator()

    portfolio = lakctx.Portfolio()
    account_name = portfolio.GetAccountNameBySubStr(account)
    click.echo(portfolio.GetAccount(account_name).String())


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
    lakctx.OptionalSeparator()

    portfolio = lakctx.Portfolio()
    account_name, asset_name = portfolio.GetAssetNameBySubStr(
        account if account is not None else '', asset)
    click.echo(portfolio.GetAccount(
        account_name).GetAsset(asset_name).String())


@lak.group()
def edit():
    """Edit parts of the portfolio."""
    pass


_HELP_MSG_PREFIX = ('\n\n# # Lines starting with "#" are ignored and an '
                    'empty message aborts this command.\n\n')


def EditAndParse(edit_dict, parse_fn, filename):
    """Helper funtion to edit parts of portfolio.

    This function is used to add/edit parts of the portfolio. It converts
    a dictionary representation of the object into a YAML file that the
    user can edit. The file is then converted back to a dictionary, which
    is parsed via the parse_fn to convert it into an object.

    Arguments:
        edit_dict: Dictionary representing an object that is being
        editted. This is usually the output of ToDict() of an object.
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
    filepath = (Path(__file__).parents[1].absolute() /
                'data' / filename)
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
        raise click.ClickException('Portfolio file already exists: ' +
                                   lakctx.portfolio_filename)

    asset_class = EditAndParse(
        None,
        lambda x: lakshmi.AssetClass.FromDict(x).Validate(),
        'AssetClass.yaml')
    lakctx.portfolio = Portfolio(asset_class)
    lakctx.SavePortfolio()


@edit.command()
def assetclass():
    """Edit the Asset classes and the desired asset allocation."""
    global lakctx
    portfolio = lakctx.Portfolio()

    asset_classes = EditAndParse(
        portfolio.asset_classes.ToDict(),
        lambda x: lakshmi.AssetClass.FromDict(x).Validate(),
        'AssetClass.yaml')
    portfolio.asset_classes = asset_classes
    lakctx.SavePortfolio()


@edit.command()
@click.option('--account', '-t', type=str, metavar='substr', required=True,
              help='Edit the account that matches this substring')
def account(account):
    """Edit an account in the portfolio."""
    global lakctx
    portfolio = lakctx.Portfolio()

    account_name = portfolio.GetAccountNameBySubStr(account)
    account_obj = portfolio.GetAccount(account_name)
    # Save assets and restore them after the user is done editing.
    assets = account_obj.Assets()
    account_obj.SetAssets([])

    account_obj = EditAndParse(
        account_obj.ToDict(),
        lakshmi.Account.FromDict,
        'Account.yaml')
    account_obj.SetAssets(assets)

    if account_obj.Name() != account_name:
        portfolio.RemoveAccount(account_name)
    portfolio.AddAccount(account_obj, replace=True)
    lakctx.SavePortfolio()


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
    portfolio = lakctx.Portfolio()

    account_name, asset_name = portfolio.GetAssetNameBySubStr(
        account if account is not None else '', asset)
    account_obj = portfolio.GetAccount(account_name)
    asset_obj = account_obj.GetAsset(asset_name)

    asset_obj = EditAndParse(asset_obj.ToDict(),
                               asset_obj.FromDict,
                               asset_obj.__class__.__name__ + '.yaml')

    if asset_obj.ShortName() != asset_name:
        account_obj.RemoveAsset(asset_name)
    account_obj.AddAsset(asset_obj, replace=True)

    lakctx.SavePortfolio()


@lak.group()
def add():
    """Add new accounts or assets to the portfolio."""
    pass


@add.command()
def account():
    """Add a new account to the portfolio."""
    global lakctx
    portfolio = lakctx.Portfolio()

    account = EditAndParse(None, lakshmi.Account.FromDict, 'Account.yaml')
    portfolio.AddAccount(account)
    lakctx.SavePortfolio()


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
    portfolio = lakctx.Portfolio()

    account_name = portfolio.GetAccountNameBySubStr(account)
    account_obj = portfolio.GetAccount(account_name)
    asset_cls = [
        c for c in lakshmi.assets.CLASSES if c.__name__ == asset_type][0]

    asset_obj = EditAndParse(None, asset_cls.FromDict, asset_type + '.yaml')
    account_obj.AddAsset(asset_obj)

    lakctx.SavePortfolio()


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
    portfolio = lakctx.Portfolio()
    account_name = portfolio.GetAccountNameBySubStr(account)
    portfolio.RemoveAccount(account_name)
    lakctx.SavePortfolio()


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
    portfolio = lakctx.Portfolio()

    account_name, asset_name = portfolio.GetAssetNameBySubStr(
        account if account is not None else '', asset)
    account_obj = portfolio.GetAccount(account_name)
    account_obj.RemoveAsset(asset_name)
    lakctx.SavePortfolio()


@lak.group(chain=True)
def analyze():
    """Analyze the portfolio. """
    pass


@analyze.command()
@click.option('--max-percentage', '-p', type=float, default=10,
              show_default=True,
              help='The max percenatage loss for each lot before TLHing.')
@click.option('--max-dollars', '-d', type=int,
              help='The max absolute loss for an asset (across all tax lots) '
              'before TLHing.')
def tlh(max_percentage, max_dollars):
    """Shows which tax lots can be Tax-loss harvested."""
    global lakctx
    lakctx.OptionalSeparator()
    table = lakshmi.analyze.TLH(max_percentage / 100, max_dollars).Analyze(
        lakctx.Portfolio())
    if not table.List():
        click.echo('No tax lots to harvest.')
    else:
        click.echo(table.String())


@analyze.command()
@click.option('--max-abs-percentage', '-a', type=float, default=5,
              show_default=True,
              help='Max absolute difference before rebalancing.')
@click.option('--max-relative-percentage', '-r', type=float, default=25,
              help='The max relatve differnce before rebalancing.')
def rebalance(max_abs_percentage, max_relative_percentage):
    """Shows if assets needs to be rebalanced based on a band
    based rebalancing scheme. For more information, please refer to
    https://www.whitecoatinvestor.com/rebalancing-the-525-rule/."""
    global lakctx
    lakctx.OptionalSeparator()
    table = lakshmi.analyze.BandRebalance(
        max_abs_percentage / 100, max_relative_percentage / 100).Analyze(
        lakctx.Portfolio())
    if not table.List():
        click.echo('Portfolio Asset allocation within bounds.')
    else:
        click.echo(table.String())


if __name__ == '__main__':
    lak()
