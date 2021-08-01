# Lakshmi

## Background
This project is inspired by
[Bogleheads forum](http://bogleheads.org). This forum taught me to focus on important
things like asset allocation, location and minimizing costs. The focus is on
simple but [powerful philosophy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy)
that allows investors to acheive above-average
returns after costs. This tool is build around the same principles to help
an _average_ investor manage their investing portfolio.

Lakshmi (meaning 'She who leads to one's goal') is one of the principal
goddesses in Hinduism. She is the goddess of wealth, fortune, power, health,
love, beauty, joy and prosperity.

## Introduction
This project consists of a library module (_lakshmi_) and a command-line
tool (_lak_) that exposes some of the functionality of the library. The library
provides useful abstractions and tools to manage your investing portfolio.

[Bogleheads wiki](https://www.bogleheads.org/wiki/Main_Page) is a great
resource for introduction to basic investing concepts like asset-allocation,
asset-location, etc.

Following features are currently available:
- Specify and track asset allocation across accounts.
- Ability to add/edit/delete accounts and assets (funds, stocks, etc.)
inside those accounts.
- Supports manual assets, assets with ticker, Vanguard funds (that don't
have associated ticker symbols),
[EE Bonds](https://www.treasurydirect.gov/indiv/products/prod_eebonds_glance.htm)
and
[I Bonds](https://www.treasurydirect.gov/indiv/research/indepth/ibonds/res_ibonds.htm).
- Automatic fetching of market value of various types of assets.
- Listing current values of assets, printing detailed information,
printing asset allocation, asset location, etc.
- Tracking of tax-lot information for assets.
- Support for running what-if scenarios to see how it impacts the asset
allocation, etc.
- Analysis of portfolio to identify if there is need to rebalance or
if there are losses that can be
[harvested](https://www.bogleheads.org/wiki/Tax_loss_harvesting).

## Installation

This project can be installed via [pip](https://pip.pypa.io/en/stable/).
To install the library and the lak command line tool, run:
```
pip install lakshmi
```

## Command-line interface

The simplest way to use this project is via the **lak** command. To access the
upto help, run:

```
$ lak --help

Usage: lak [OPTIONS] COMMAND [ARGS]...

Options:
  --version      Show the version and exit.
  -r, --refresh  Re-fetch all data instead of using previously cached data.
                 For large portfolios this would be extremely slow.
  --help         Show this message and exit.

Commands:
  add      Add new accounts or assets to the portfolio.
  analyze  Analyze the portfolio.
  delete   Delete an account or asset.
  edit     Edit parts of the portfolio.
  info     Prints detailed information about an asset or account.
  init     Initializes a new portfolio by adding asset classes.
  list     Command to list various parts of the portfolio.
  whatif   Run hypothetical what if scenarios by adding DELTA to an...
```

A new portfolio can be created by either:
1. Copying an [existing](data/portfolio.yaml) portfolio file to
~/portfolio.yaml and editing it.

-- OR --

2. Using the lak commands to create a new portfolio. The following command will
open up an editor to input the desired asset allocation:
```
lak init
```

To view help for the init command, please run:
```
lak init --help
```

Accounts (His/Her 401(k), Roth IRAs, Taxable, etc.) can be added via
the **lak add account** command:
```
lak add account
```
Assets can be added to the account via the **lak add asset** command. Different
kinds of assets can be added to a portfolio. For a complete list, pull up the
help for the command:
```
$ lak add asset --help

Usage: lak add asset [OPTIONS]

  Edit assets in the portfolio.

Options:
  -p, --asset-type [ManualAsset|TickerAsset|VanguardFund|IBonds|EEBonds]
                                  Add this type of asset.  [required]
  -t, --account substr            Add asset to this account (a sub-string that
                                  matches the account name).  [required]
  --help                          Show this message and exit.
```

TickerAsset represents an asset with a ticker symbol. The value of these assets
is pulled and updated automatically. To add a TickerAsset:

```
lak add asset -p TickerAsset -t account_str
```
where account_str is a sub-string that uniquely matches an account added previously.

That's it. To view all the assets, asset allocation and asset location, run:
```
lak list assets
lak list total
lak list aa
lak list al
```
The **lak list** commands can also be chained:
```
lak list assets total aa al
```

[TODO: Detailed Description of the tool](docs/lak.md)

## Library

TODO: Add details about the lakshmi module.

## Dedication

I would like to thank my wife [Niharika](http://niharika.org), who encouraged me to
start working on this package and supported me throughout the development.
This project would not have been possible without her love and support.

In addition, I am indebted to the following folks whose wisdom has helped me
tremendously in my investing journey:
[John Bogle](https://en.wikipedia.org/wiki/John_C._Bogle),
[Taylor Larimore](https://www.bogleheads.org/wiki/Taylor_Larimore),
[Nisiprius](https://www.bogleheads.org/forum/viewtopic.php?t=242756),
[Livesoft](https://www.bogleheads.org/forum/viewtopic.php?t=237269),
[Mel Lindauer](https://www.bogleheads.org/wiki/Mel_Lindauer) and
[LadyGeek](https://www.bogleheads.org/blog/2018/12/04/interview-with-ladygeek-bogleheads-site-administrator/).
