import click
from lakshmi import Portfolio
import lakshmi.assets
import lakshmi.cache
from lakshmi.table import Table
from pathlib import Path
import yaml


class LakContext:
    def _ReturnConfig(self):
        lakrcfile = Path(self.lakrc).expanduser()

        if not lakrcfile.exists():
            return {}
        config = yaml.load(lakrcfile.read_text(), Loader=yaml.SafeLoader)
        return config

    def __init__(self, lakrc='~/.lakrc'):
        self.lakrc = lakrc
        self.continued = False
        self.whatifs = None
        config = self._ReturnConfig()

        portfolio_filename = config.pop('portfolio', '~/portfolio.yaml')
        self.portfolio_filename = str(Path(portfolio_filename).expanduser())
        self._portfolio = Portfolio.Load(self.portfolio_filename)

        if 'cache' in config:
            cache_dir = config.pop('cache')
            if cache_dir is None:
                lakshmi.cache.set_cache_dir(None)
            else:
                lakshmi.cache.set_cache_dir(Path(cache_dir).expanduser())

        assert len(config) == 0, (
            f'Extra entries found in config file: {list(config.keys())}')

    def Separator(self):
        if self.continued:
            click.echo('\n')
        # Set it up so that separator is printed for the next command.
        self.continued = True

    def GetWhatIfs(self):
        if not self.whatifs:
            self.whatifs = self.Portfolio().GetWhatIfs()
        return self.whatifs

    def WarnForWhatIfs(self):
        if self.continued:
            return

        self.GetWhatIfs()
        if self.whatifs[0].List() or self.whatifs[1].List():
            click.secho('Warning: Hypothetical what ifs are set.\n', fg='red')

    def Portfolio(self):
        return self._portfolio

    def SavePortfolio(self):
        self._portfolio.Save(self.portfolio_filename)


lakctx = None

@click.group()
@click.version_option()
@click.option('--refresh', '-r', is_flag=True,
        help='Fetch new data instead of using previously cached data.')
def lak(refresh):
    lakshmi.cache.set_force_refresh(False)
    global lakctx
    if not lakctx:
        lakctx = LakContext()
        lakshmi.cache.set_force_refresh(refresh)


@lak.group(chain=True)
def list():
    """Command to list various parts of the portfolio."""
    global lakctx


@list.command()
def total():
    """Prints the total value."""
    global lakctx
    lakctx.WarnForWhatIfs()
    lakctx.Separator()
    portfolio = lakctx.Portfolio()
    click.echo(
        Table(2, coltypes=['str', 'dollars']).AddRow(
            ['Total Assets', portfolio.TotalValue()]).String())


@list.command()
def al():
    """Prints the Asset Location."""
    global lakctx
    lakctx.WarnForWhatIfs()
    lakctx.Separator()
    portfolio = lakctx.Portfolio()
    click.echo(portfolio.AssetLocation().String())


@list.command()
@click.option('--compact/--no-compact', default=True, show_default=True,
        help='Print the Asset allocation tree in a compact format')
@click.option('--asset-class', '-a', type=str,
        help='If provided, only print asset allocation for these asset '
        'classes. This is comma seperate list of asset classes (not '
        'necessarily leaf asset classes) and the allocation across these '
        'asset classes should sum to 100%.')
def aa(compact, asset_class):
    """Prints the Asset Allocation."""
    global lakctx
    lakctx.WarnForWhatIfs()
    lakctx.Separator()
    portfolio = lakctx.Portfolio()
    if asset_class:
        assert compact, ('--no-compact is only supported when --asset-class'
                'is not specified.')
        classes_list = [c.strip() for c in asset_class.split(',')]
        click.echo(portfolio.AssetAllocation(classes_list).String())
    else:
        if compact:
            click.echo(portfolio.AssetAllocationCompact().String())
        else:
            click.echo(portfolio.AssetAllocationTree().String())


@list.command()
@click.option('--short-name', '-s', is_flag=True,
        help='Print the short name of the assets as well (e.g. Ticker for '
        'assets that have it)')
@click.option('--quantity', '-q', is_flag=True,
        help='Print the quantity of the asset (e.g. quantity/shares for '
        'assets that support it)')
def assets(short_name, quantity):
    """Prints Assets and their current values."""
    global lakctx
    lakctx.WarnForWhatIfs()
    lakctx.Separator()
    portfolio = lakctx.Portfolio()
    click.echo(portfolio.Assets(short_name=short_name,
        quantity=quantity).String())


@list.command()
def whatifs():
    """Print hypothetical what ifs for assets and accounts."""
    global lakctx
    account_whatifs, asset_whatifs = lakctx.GetWhatIfs()
    if account_whatifs.List():
        lakctx.Separator()
        click.echo(account_whatifs.String())
    if asset_whatifs.List():
        lakctx.Separator()
        click.echo(asset_whatifs.String())


@lak.command(context_settings={"ignore_unknown_options": True})
@click.option('--asset', '-a', type=str, metavar='substr',
        help='Make changes to this asset (a sub-string that matches either'
        ' the asset name or the short name)')
@click.option('--account', '-t', type=str, metavar='substr',
        help='Make changes to this account (a sub-string that matches the'
        ' account name)')
@click.option('--reset', '-r', is_flag=True,
        help='Reset all hypothetical whatif amounts.')
@click.argument('delta', type=float, required=False)
def whatif(asset, account, reset, delta):
    """Run hypothetical what if scenarios by adding DELTA to an account
    or asset."""
    # Sanity check the flags.
    global lakctx
    portfolio = lakctx.Portfolio()

    if reset:
        assert asset is None and account is None and delta is None, (
                'Can\'t specify any other flags/arguments when --reset is '
                'specified')
        portfolio.ResetWhatIfs()
        lakctx.SavePortfolio()
        return

    assert delta is not None, ('Must specify a value (delta) to add/subtract '
            'from an account or asset')

    if asset is None and account is not None:  # Delta is applied to Account
        account_name = portfolio.GetAccountNameBySubStr(account)
        portfolio.WhatIfAddCash(account_name, delta)
        lakctx.SavePortfolio()
        return

    if asset is not None:
        account_name, asset_name = portfolio.GetAssetNameBySubStr(
                account if account is not None else '', asset)
        portfolio.WhatIf(account_name, asset_name, delta)
        lakctx.SavePortfolio()
        return

    raise click.UsageError('At least one of --asset or --account must '
            'be specified')

@lak.command()
@click.option('--asset', '-a', type=str, metavar='substr',
        help='Get Info about this asset (a sub-string that matches either '
        'the asset name or the short name)')
@click.option('--account', '-t', type=str, metavar='substr',
        help='Get Info about this account (a sub-string that matches the '
        'account name)')
def info(asset, account):
    """Prints detailed information about an asset or account. If only account
    is specified, this command prints information about an account. If asset
    or both asset and acccount is specified, it prints information about an
    asset. In the second case, asset (and optionally account) must match
    exactly one asset in the portfolio."""
    global lakctx
    portfolio = lakctx.Portfolio()

    if asset is None and account is not None:
        account_name = portfolio.GetAccountNameBySubStr(account)
        click.echo(portfolio.GetAccount(account_name).String())
        return

    if asset is not None:
        account_name, asset_name = portfolio.GetAssetNameBySubStr(
                account if account is not None else '', asset)
        click.echo(portfolio.GetAccount(account_name).GetAsset(asset_name).String())
        return

    raise click.UsageError('At least one of --asset or --account'
            ' must be specified')


@lak.group()
def edit():
    """Edit, add or delete parts of the portfolio."""
    pass


def edit_and_parse(edit_dict, parse_fn, help_filename=None):
    HELP_MSG = ('\n\n' + '# # Lines starting with "#" are ignored and an empty '
            'message aborts this command.\n\n')
    if help_filename:
        help_filepath = (Path(__file__).parents[2].absolute() /
                'data' / help_filename)
        HELP_MSG += help_filepath.read_text()

    original_str = edit_str = yaml.dump(edit_dict, sort_keys=False) + HELP_MSG
    while True:
        edit_str = click.edit(edit_str)
        if not edit_str or original_str == edit_str:
            click.echo('No changes made.')
            return None
        edit_str.split(HELP_MSG, 1)[0].rstrip('\n')
        try:
            return parse_fn(yaml.load(edit_str.split(
                HELP_MSG, 1)[0].rstrip('\n'), Loader=yaml.SafeLoader))
        except Exception as e:
            click.echo('Error parsing file: ' + repr(e))
            if not click.confirm('Do you want to edit again?'):
                click.echo('No changes made.')
                return None


@edit.command()
def assetclass():
    """Edit the Asset classes and desired AA across those asset classes."""
    global lakctx
    portfolio = lakctx.Portfolio()

    asset_classes = edit_and_parse(
            portfolio.asset_classes.ToDict(),
            lambda x: lakshmi.AssetClass.FromDict(x).Validate(),
            'AssetClass.yaml')
    if asset_classes is None:
        return
    portfolio.asset_classes = asset_classes
    lakctx.SavePortfolio()


@edit.command()
@click.option('--account', '-t', type=str, metavar='substr',
        help='Edit the account that matches this sub-string')
def account(account):
    """Edit accounts in the portfolio."""
    if account is None:
        raise click.BadParameter('--account must be specified')

    global lakctx
    portfolio = lakctx.Portfolio()

    account_name = portfolio.GetAccountNameBySubStr(account)
    account_obj = portfolio.GetAccount(account_name)
    assets = account_obj.Assets()
    account_obj.SetAssets([])

    account_obj = edit_and_parse(
            account_obj.ToDict(),
            lakshmi.Account.FromDict,
            'Account.yaml')
    if account_obj is None:
        return
    account_obj.SetAssets(assets)

    if account_obj.Name() != account_name:
        portfolio.RemoveAccount(account_name)
    portfolio.AddAccount(account_obj, replace=True)
    lakctx.SavePortfolio()


@edit.command()
@click.option('--asset', '-a', type=str, metavar='substr', required=True,
        help='Get Info about this asset (a sub-string that matches either '
        'the asset name or the short name)')
@click.option('--account', '-t', type=str, metavar='substr',
        help='Get Info about this account (a sub-string that matches the '
        'account name)')
def asset(asset, account):
    """Edit assets in the portfolio."""
    global lakctx
    portfolio = lakctx.Portfolio()

    account_name, asset_name = portfolio.GetAssetNameBySubStr(
            account if account is not None else '', asset)
    account_obj = portfolio.GetAccount(account_name)
    asset_obj = account_obj.GetAsset(asset_name)

    asset_obj = edit_and_parse(asset_obj.ToDict(),
            asset_obj.FromDict,
            asset_obj.__class__.__name__ + '.yaml')

    if asset_obj is None:
        return

    if asset_obj.ShortName() != asset_name:
        account_obj.RemoveAsset(asset_name)
    account_obj.AddAsset(asset_obj, replace=True)

    lakctx.SavePortfolio()


if __name__ == '__main__':
    lak()
