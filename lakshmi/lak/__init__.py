import click
from lakshmi import Portfolio
import lakshmi.cache
from lakshmi.table import Table
from pathlib import Path
import yaml


class LakConfig:
    LAKRC = '.lakrc'

    def _ReturnConfig(self):
        lakrcfile = Path.home() / self.LAKRC

        if not lakrcfile.exists():
            return {}
        config = yaml.load(lakrcfile.read_text(), Loader=yaml.SafeLoader)
        return config

    def __init__(self):
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

    def Portfolio(self):
        return self._portfolio

    def SavePortfolio(self):
        self._portfolio.Save(self.portfolio_filename)


lakconfig = LakConfig()
continued = False


def Separator():
    """Prints separator if multiple commands are chained."""
    global continued
    if continued:
        click.echo('\n')
    # Set it up so that separator is printed for the next command.
    continued = True


@click.group()
@click.option('--force-refresh/--no-force-refresh',
        default=False,
        show_default=True,
        help='If set, fetches new data instead of using cached data.')
def lak(force_refresh):
    lakshmi.cache.set_force_refresh(force_refresh)


@lak.group(chain=True)
def list():
    """Command to list various parts of the portfolio."""
    pass

@list.command()
def total():
    """Prints the total value."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    click.echo(
        Table(2, coltypes=['str', 'dollars']).AddRow(
            ['Total Assets', portfolio.TotalValue()]).String())


@list.command()
def al():
    """Prints the Asset Location."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    click.echo(portfolio.AssetLocation().String())


@list.command()
@click.option('--compact/--no-compact', default=True, show_default=True,
        help='If true, prints the Asset allocation tree in a compact format')
@click.option('--asset-class', default='', type=str,
        help='If provided, only prints asset allocation for these asset classes. '
        'This is comma seperate list of asset classes (not necessarily '
        'leaf asset classes) and the allocation across these asset classes '
        'should sum to one.')
def aa(compact, asset_class):
    """Prints the Asset Allocation."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
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
@click.option('--short-name/--no-short-name', default=False, show_default=True,
        help='If set, prints the Short name of the assets as well (e.g. Ticker for '
        'assets that have it)')
@click.option('--quantity/--no-quantity', default=False, show_default=True,
        help='If set, prints the quantity of the asset (e.g. quantity or shares for '
        'assets that support it)')
def assets(short_name, quantity):
    """Prints Assets and their current values."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    click.echo(portfolio.Assets(short_name=short_name, quantity=quantity).String())

@lak.command(context_settings={"ignore_unknown_options": True})
@click.option('--asset', type=str,
        help='Make changes to this asset (a sub-string that matches either the asset name or the short name)')
@click.option('--account', type=str,
        help='Make changes to this account (a sub-string that matches the account name)')
@click.option('--reset/--no-reset', default=False,
        help='If set, reset all hypothetical whatif amounts.')
@click.argument('delta', type=float, required=False)
def whatif(asset, account, reset, delta):
    """Run hypothetical what if scenarios."""
    # Sanity check the flags.
    global lakconfig
    portfolio = lakconfig.Portfolio()

    if reset:
        assert asset is None and account is None and delta is None, (
                'Can\'t specify any other flags/arguments when --reset is '
                'specified')
        portfolio.ResetWhatIfs()
        lakconfig.SavePortfolio()
        return

    assert delta is not None, ('Must specify a value (delta) to add/subtract '
            'from an account or asset')

    if asset is None and account is not None:  # Delta is applied to Account
        account_name = portfolio.GetAccountNameBySubStr(account)
        portfolio.WhatIfAddCash(account_name, delta)
        lakconfig.SavePortfolio()
        return

    if asset is not None:
        account_name, asset_name = portfolio.GetAssetNameBySubStr(
                account if account is not None else '', asset)
        portfolio.WhatIf(account_name, asset_name, delta)
        lakconfig.SavePortfolio()
        return

    raise click.ClickException('One of asset or account must be provided.')


if __name__ == '__main__':
    lak()
