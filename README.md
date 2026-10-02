# Lakshmi

[![PyPI version](https://badge.fury.io/py/lakshmi.svg)](https://badge.fury.io/py/lakshmi)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sarvjeets/lakshmi/develop.svg)](https://results.pre-commit.ci/latest/github/sarvjeets/lakshmi/develop)
[![Downloads](https://pepy.tech/badge/lakshmi)](https://pepy.tech/project/lakshmi)
[![Downloads](https://pepy.tech/badge/lakshmi/month)](https://pepy.tech/project/lakshmi)

![Screenshot of lak in action](https://sarvjeets.github.io/lakshmi/docs/lak.png)
(Screenshot of the `lak` command in action)

Lakshmi is an open-source Python library and CLI tool for index-investing
portfolio management.

## Why Lakshmi?

Most modern portfolio trackers require sharing sensitive credentials with
third-party servers, struggle with tax-location strategies, or push active
trading features. Lakshmi takes a different approach:

* **🔒 Privacy & Local-First:** Your financial data stays entirely on your
local machine in plain-text/YAML formats. No third-party data tracking or
account syncing required.
* **🎯 True Asset Location:** Manage your total allocation seamlessly across
Taxable, Tax-Deferred (401k, Traditional IRA), and Tax-Exempt (Roth IRA)
accounts.
* **⚖️ Actionable Rebalancing & What-Ifs:** Doesn't just show values — calculates
exactly how to allocate new contributions (or withdrawals) to restore your
target allocation.
* **💡 Advanced Tax Awareness:** Integrated tax-lot tracking, tax-loss
harvesting alerts, and native support for unique fixed-income assets like
Treasury I/EE Bonds and Vanguard non-ticker funds.

## Background
This project is inspired by
[Bogleheads forum](http://bogleheads.org). Bogleheads focus on a simple but
[powerful philosophy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy)
that allows investors to achieve above-average
returns after costs. This tool is built around the same principles to help
an _average_ investor manage their investing portfolio.

Lakshmi (meaning "She who leads to one's goal") is one of the principal
goddesses in Hinduism. She is the goddess of wealth, fortune, power, health,
love, beauty, joy and prosperity.

## Introduction
This project consists of a library module (`lakshmi`) and a command-line
tool (`lak`) that exposes some of the functionality of the library. The library
provides useful abstractions and tools to manage your investing portfolio.

[Bogleheads wiki](https://www.bogleheads.org/wiki/Main_Page) is a great
resource for introduction to basic investing concepts like asset-allocation,
asset-location, etc.

The following features are currently available:

- Specify and track asset allocation across accounts.
- Ability to add/edit/delete accounts and assets (funds, stocks, ETFs, etc.)
inside those accounts. The market value of these assets is automatically
updated.
- Support for running what-if scenarios to see how it impacts the overall asset
allocation.
- Suggests which funds to allocate new money to (or withdraw money from) to
keep the actual asset allocation close to the desired asset allocation.
- Suggests how to rebalance the funds in a given account to bring the actual
asset allocation close to the desired asset allocation.
- Ability to track portfolio performance
([IRR](https://www.investopedia.com/terms/i/irr.asp#:~:text=The%20internal%20rate%20of%20return,a%20discounted%20cash%20flow%20analysis.))
and cash flows.
- Supports manual assets, assets with ticker, Vanguard funds (that don't
have associated ticker symbols),
[EE Bonds](https://www.treasurydirect.gov/indiv/products/prod_eebonds_glance.htm)
and
[I Bonds](https://www.treasurydirect.gov/indiv/research/indepth/ibonds/res_ibonds.htm).
- Listing current values of assets, asset allocation and asset location.
- Tracking of tax-lot information for assets.
- Analysis of portfolio to identify if there is need to rebalance or
if there are losses that can be
[harvested](https://www.bogleheads.org/wiki/Tax_loss_harvesting).

## Installation

This project can be installed via [PyPI](https://pypi.org/project/lakshmi/).
You can use either [pip](https://pip.pypa.io/en/stable/) or
[pipx](https://pipx.pypa.io/stable/) to install it:

```
# Install via pip
pip install lakshmi
# Or, pipx
pipx install lakshmi
```

Or, on Arch Linux, you can install it from
[AUR](https://aur.archlinux.org/packages/python-lakshmi) via
[AUR helpers](https://wiki.archlinux.org/title/AUR_helpers)
or [directly](https://wiki.archlinux.org/title/Arch_User_Repository)
```
yay -S python-lakshmi
```

## Command-line interface

For detailed help on the CLI, please see [lak user guide](https://sarvjeets.github.io/lakshmi/docs/lak.html).
For tips and tricks, please refer to [Lakshmi Recipes](https://sarvjeets.github.io/lakshmi/docs/recipes.html).

The simplest way to use this project is via the `lak` command. To access the
up to date help, run:

```
$ lak --help
Usage: lak [OPTIONS] COMMAND [ARGS]...

  lak is a simple command line tool inspired by Bogleheads philosophy.
  Detailed user guide is available at:
  https://sarvjeets.github.io/lakshmi/docs/lak.html

Options:
  --version          Show the version and exit.
  -r, --refresh      Re-fetch all data instead of using previously cached
                     data. For large portfolios, this would be extremely slow.
  -c, --config PATH  The configuration file.  [env var: LAK_CONFIG; default:
                     ~/.lakrc]
  --debug            If set, prints stack track when an exception is raised.
  --help             Show this message and exit.

Commands:
  add      Add new entities to the portfolio.
  analyze  Analyze the portfolio.
  delete   Delete different entities from the portfolio.
  edit     Edit parts of the portfolio.
  info     Print detailed information about parts of the portfolio.
  init     Initializes a new portfolio by adding asset classes.
  list     Command to list various parts of the portfolio.
  whatif   Run hypothetical what if scenarios by modifying the total...
```
The following section gives a quick summary of how to create a new portfolio.
For detailed help, please read
[creating a portfolio](https://sarvjeets.github.io/lakshmi/docs/lak.html#creating-a-portfolio) section of the
[lak user guide](https://sarvjeets.github.io/lakshmi/docs/lak.html).

A new portfolio can be created by either:

1. Copying an [existing](https://sarvjeets.github.io/lakshmi/docs/portfolio.yaml)
portfolio file to ~/portfolio.yaml and editing it, OR
2. Using the `lak` commands to create a new portfolio.

The following command will open up an editor to input the desired asset
allocation:

```
$ lak init
```

Accounts (401Ks, Roth IRAs, Taxable, etc.) can be added via
the `lak add account` command:

```
$ lak add account
# Use the above command multiple times to add more accounts.
```

Assets can be added to an account via the `lak add asset` command. Different
kinds of assets can be added to a portfolio. For a complete list, pull up the
help for the command:

```
$ lak add asset --help
Usage: lak add asset [OPTIONS]

  Add a new asset to the portfolio.

Options:
  -p, --asset-type [ManualAsset|TickerAsset|VanguardFund|IBonds|EEBonds]
                                  Add this type of asset.  [required]
  -t, --account substr            Add asset to this account (a substring that
                                  matches the account name).  [required]
  --help                          Show this message and exit.
```

TickerAsset represents an asset with a ticker symbol. The value of these assets
is updated automatically. To add a TickerAsset:

```
lak add asset -p TickerAsset -t account_str
```
where account_str is a sub-string that uniquely matches an account added previously.

That's it. To view all the assets, asset allocation and asset location, run:

```
lak list assets total aa al
```

## Library

The `lakshmi` library can also be used directly. The modules and classes are
well documented and there are numerous examples for using each method or class
in the [tests](https://github.com/sarvjeets/lakshmi/tree/develop/tests)
accompanying this package. The
[example portfolio](https://sarvjeets.github.io/lakshmi/docs/portfolio.yaml) can be constructed and the asset
allocation, etc. can be printed by the following piece of python code:

```python
from lakshmi import Account, AssetClass, Portfolio
from lakshmi.assets import TaxLot, TickerAsset
from lakshmi.table import Table


def main():
    asset_class = (
        AssetClass('All')
        .add_subclass(0.6, AssetClass('Equity')
                      .add_subclass(0.6, AssetClass('US'))
                      .add_subclass(0.4, AssetClass('Intl')))
        .add_subclass(0.4, AssetClass('Bonds')))
    portfolio = Portfolio(asset_class)

    (portfolio
     .add_account(Account('Schwab Taxable', 'Taxable')
                  .add_asset(TickerAsset('VTI', 1, {'US': 1.0})
                             .set_lots([TaxLot('2021/07/31', 1, 226)]))
                  .add_asset(TickerAsset('VXUS', 1, {'Intl': 1.0})
                             .set_lots([TaxLot('2021/07/31', 1, 64.94)])))
     .add_account(Account('Roth IRA', 'Tax-Exempt')
                  .add_asset(TickerAsset('VXUS', 1, {'Intl': 1.0})))
     .add_account(Account('Vanguard 401(k)', 'Tax-Deferred')
                  .add_asset(TickerAsset('VBMFX', 20, {'Bonds': 1.0}))))

    # Save the portfolio
    # portfolio.Save('portfolio.yaml')
    print('\n' + portfolio.asset_allocation_compact().string() + '\n')
    print(Table(2, coltypes=['str', 'dollars'])
          .add_row(['Total Assets', portfolio.total_value()]).string())
    print('\n' + portfolio.asset_allocation(['US', 'Intl', 'Bonds']).string())
    print('\n' + portfolio.assets().string() + '\n')
    print(portfolio.asset_location().string())


if __name__ == "__main__":
    main()
```

## Development
Here are the steps to download the source code and start developing on
Lakshmi:

```shell
# Fork and clone this repo.
$ git clone https://github.com/yourusername/lakshmi.git
$ cd lakshmi

# All development is done on the 'develop' branch
$ git checkout develop

# Install uv if you don't have it: https://docs.astral.sh/uv/getting-started/installation/
# Install all dependencies (creates a virtual environment automatically)
$ uv sync --group dev

# Run unittests
$ uv run python -m unittest

# Install pre-commit hooks to run it automatically on commits
$ uv run pre-commit install
# Run pre-commit manually
$ uv run pre-commit run --all-files

# Create your own bug or feature branch and start developing. Remember to
# run tests (and add them when necessary) and pre-commit hooks on changes.
```

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements

I am indebted to the following folks whose wisdom has helped me
tremendously in my investing journey:
[John Bogle](https://en.wikipedia.org/wiki/John_C._Bogle),
[Taylor Larimore](https://www.bogleheads.org/wiki/Taylor_Larimore),
[Nisiprius](https://www.bogleheads.org/forum/viewtopic.php?t=242756),
[Livesoft](https://www.bogleheads.org/forum/viewtopic.php?t=237269),
[Mel Lindauer](https://www.bogleheads.org/wiki/Mel_Lindauer) and
[LadyGeek](https://www.bogleheads.org/blog/2018/12/04/interview-with-ladygeek-bogleheads-site-administrator/).

This project would not have been possible without my wife
[Niharika](https://www.niharika.org), who helped me come up with the initial
idea and encouraged me to start working on this project.


## The not-so-fine print

_The author is not a financial adviser and you agree to treat this tool
for informational purposes only. The author does not promise or guarantee
that the information provided by this tool is correct, current, or complete,
and it may contain technical inaccuracies or errors. The author is not
liable for any losses that you might incur by acting on the information
provided by this tool. Accordingly, you should confirm the accuracy and
completeness of all content, and seek professional advice taking into
account your own personal situation, before making any decision based
on information from this tool._

In a nutshell:
* The information provided by this tool is not financial advice.
* The author is not an expert or financial adviser.
* Consult a financial and/or tax adviser before taking action.
