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
        portfolio_filename = str(Path(portfolio_filename).expanduser())
        self._portfolio = Portfolio.Load(portfolio_filename)

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

    def SavePortfolio(self, portfolio):
        self._portfolio = portfolio
        portfolio.Save(self._portfoliofilename)


lakconfig = LakConfig()
continued = False


def Separator():
    """Prints separator if multiple commands are chained."""
    global continued
    if continued:
        click.echo('\n')
    # Set it up so that separator is printed for the next command.
    continued = True


@click.group(chain=True)
@click.option('--force-refresh/--no-force-refresh',
              default=False,
              show_default=True,
              help='If set, fetches new data instead of using cached data.')
def lak(force_refresh):
    lakshmi.cache.set_force_refresh(force_refresh)


@lak.command()
def total():
    """Prints the total value."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    click.echo(
        Table(2, coltypes=['str', 'dollars']).AddRow(
            ['Total Assets', portfolio.TotalValue()]).String())


@lak.command()
def al():
    """Prints the Asset Location."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    click.echo(portfolio.AssetLocation().String())


@lak.command()
@click.option('--compact/--no-compact', default=True, show_default=True,
              help='If true, prints the Asset allocation tree in a compact format')
@click.argument('assets', nargs=-1)
def aa(compact, assets):
    """Prints the Asset Allocation. If assets are provided, only prints asset
    allocation for these asset classes. The allocation across these asset
    classes should sum to one.
    """
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    if assets:
        assert compact, ('--no-compact is only supported when assets '
                         'are not provided.')
        click.echo(portfolio.AssetAllocation(assets).String())
    else:
        if compact:
            click.echo(portfolio.AssetAllocationCompact().String())
        else:
            click.echo(portfolio.AssetAllocationTree().String())


@lak.command()
def assets():
    """Prints Assets and their current values."""
    Separator()
    global lakconfig
    portfolio = lakconfig.Portfolio()
    click.echo(portfolio.Assets().String())


if __name__ == '__main__':
    lak()
