import click
from lakshmi import Portfolio
import lakshmi.cache
from lakshmi.table import Table
import pathlib
import yaml


class LakConfig:
  LAKRC = '.lakrc'
  def _ReturnConfig(self):
    lakrcfilename = pathlib.PurePath.joinpath(
      pathlib.Path.home(),
      self.LAKRC)

    if not lakrcfilename.exists():
      return {}

    with open(lakrcfilename) as lakrcfile:
      config = yaml.load(lakrcfile.read(), Loader=yaml.SafeLoader)
    return config

  def __init__(self):
    config = self._ReturnConfig()
    portfolio_file = config.pop(
      'portfolio',
      str(pathlib.PurePath.joinpath(
        pathlib.Path.home(), 'portfolio.yaml')))
    self._portfolio = Portfolio.Load(portfolio_file)

    lakshmi.cache.CACHE_DIR = config.pop(
      'cache',
      str(pathlib.PurePath.joinpath(
        pathlib.Path.home(), '.lakshmicache')))

  def Portfolio(self):
    return self._portfolio

  def SavePortfolio(self, portfolio):
    self._portfolio = portfolio
    portfolio.Save(self._portfoliofilename)

lakconfig = LakConfig()
continued=False
def Separator():
  """Prints separator if multiple commands are chained."""
  global continued
  if continued:
    click.echo('\n')
  # Set it up so that separator is printed for the next command.
  continued=True


@click.group(chain=True)
def lak():
  pass


@lak.command()
def total():
  """Prints the total value."""
  Separator()
  global lakconfig
  portfolio = lakconfig.Portfolio()
  click.echo(
    Table(2, coltypes = ['str', 'dollars']).AddRow(
      ['Total Assets', portfolio.TotalValue()]).String())


@lak.command()
def al():
  """Prints the Asset Location."""
  Separator()
  global lakconfig
  portfolio = lakconfig.Portfolio()
  click.echo(portfolio.AssetLocation().String())


@lak.command()
@click.option('--compact/--no-compact',
              default=True,
              help='If true, prints the Asset allocation tree in a compact format')
@click.option('--asset-class',
              default='',
              type=str,
              help='If set, only prints asset allocation for these asset classes')
def aa(compact, asset_class):
  """Prints the Asset Allocation."""
  Separator()
  global lakconfig
  portfolio = lakconfig.Portfolio()
  if asset_class:
    assert compact, ('--no-compact is only supported when --asset-class' +
                     'is not specified.')
    classes_list = asset_class.split(',')
    click.echo(portfolio.AssetAllocation(classes_list).String())
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
