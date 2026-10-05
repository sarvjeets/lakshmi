# Lakshmi

[![PyPI version](https://badge.fury.io/py/lakshmi.svg)](https://badge.fury.io/py/lakshmi)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sarvjeets/lakshmi/develop.svg)](https://results.pre-commit.ci/latest/github/sarvjeets/lakshmi/develop)
[![Downloads](https://pepy.tech/badge/lakshmi)](https://pepy.tech/project/lakshmi)
[![Downloads](https://pepy.tech/badge/lakshmi/month)](https://pepy.tech/project/lakshmi)

![Screenshot of lak in action](https://sarvjeets.github.io/lakshmi/docs/lak.png)
(Screenshot of the `lak` command in action)

Lakshmi is an open-source Python library and command-line tool (`lak`) for
managing an index-investing portfolio, inspired by the
[Bogleheads](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy)
philosophy. It is built for US investors and reports values in dollars.

## Why Lakshmi?

Most modern portfolio trackers require sharing sensitive credentials with
third-party servers, struggle with tax-location strategies, or push active
trading features. Lakshmi takes a different approach:

* **🔒 Privacy & Local-First:** Your portfolio lives in a plain-text YAML file
on your machine. There are no accounts to link and no credentials to share.
The only network access is looking up public prices for the tickers you hold.
* **🎯 Asset Allocation & Location:** Track your target allocation across
Taxable, Tax-Deferred (401(k), Traditional IRA) and Tax-Exempt (Roth IRA)
accounts, and see how each asset class is spread across account types.
* **⚖️ Actionable Rebalancing & What-Ifs:** Doesn't just show values. Try
hypothetical trades, and get suggestions for where to put new contributions
(or take withdrawals from) to move back toward your target allocation.
* **💡 Tax Awareness:** Tax-lot tracking, tax-loss harvesting candidates, and
native support for Treasury I/EE Bonds and Vanguard funds without tickers.
* **📈 Performance Tracking:** Dollar-weighted returns (IRR) computed from
periodic portfolio checkpoints, with contributions and withdrawals recorded as
cash flows.

## Installation

Lakshmi requires Python 3.9 or newer and is available on
[PyPI](https://pypi.org/project/lakshmi/). To use the `lak` command, install it
with [pipx](https://pipx.pypa.io/stable/) (or
[uv](https://docs.astral.sh/uv/)), which keeps it in its own environment:

```
pipx install lakshmi
# Or, with uv
uv tool install lakshmi
```

To use Lakshmi as a library, `pip install lakshmi` inside your project's
environment.

On Arch Linux, you can also install it from the
[AUR](https://aur.archlinux.org/packages/python-lakshmi) via an
[AUR helper](https://wiki.archlinux.org/title/AUR_helpers) or
[manually](https://wiki.archlinux.org/title/Arch_User_Repository):

```
yay -S python-lakshmi
```

## Quick start

The fastest way to see what Lakshmi does is to try it on the example portfolio:

```
curl -o ~/portfolio.yaml https://sarvjeets.github.io/lakshmi/docs/portfolio.yaml
lak list assets total aa al
```

The first run is slow because it fetches names and prices. After that they are
cached (prices for a day), so later runs are fast.

To build your own portfolio, either edit a copy of the example file, or use
`lak` to create one step by step:

1. Enter your desired asset allocation: `lak init`. This opens an editor with
an example allocation. If you want to keep the example as is, make any small
edit (e.g. delete a comment) before saving, since `lak` treats an unchanged
file as an aborted edit.
2. Add your accounts (401(k), Roth IRA, Taxable, etc.) with `lak add account`.
Run it once per account.
3. Add assets to an account with `lak add asset -p TickerAsset -t <account>`,
where `<account>` is a substring that uniquely matches an account name. Other
asset types (`ManualAsset`, `VanguardFund`, `IBonds`, `EEBonds`) are listed in
`lak add asset --help`.
4. View everything with `lak list assets total aa al`.

For a detailed walkthrough, see
[creating a portfolio](https://sarvjeets.github.io/lakshmi/docs/lak.html#creating-a-portfolio)
in the [lak user guide](https://sarvjeets.github.io/lakshmi/docs/lak.html).
For tips and tricks (moving config files, shell completion, multiple
portfolios, automatic emails), see
[Lakshmi Recipes](https://sarvjeets.github.io/lakshmi/docs/recipes.html).

## Features

**Plan**

- Specify a nested target asset allocation and track it across all accounts.
- List assets, asset allocation and asset location.
- Run what-if scenarios to see how a change would affect your allocation before
you make it.

**Decide**

- Suggest which funds to put new money into (or withdraw from) to keep the
actual allocation close to the target. *(Beta)*
- Suggest how to rebalance the funds in a given account.
- Check whether any asset class has drifted outside its
[rebalancing bands](https://www.whitecoatinvestor.com/rebalancing-the-525-rule/).
- Find tax lots that are candidates for
[tax-loss harvesting](https://www.bogleheads.org/wiki/Tax_loss_harvesting).

**Track**

- Add, edit and delete accounts and assets. Market values update automatically.
- Supported assets: manual assets, anything with a ticker, Vanguard funds
without tickers,
[EE Bonds](https://www.treasurydirect.gov/indiv/products/prod_eebonds_glance.htm)
and
[I Bonds](https://www.treasurydirect.gov/indiv/research/indepth/ibonds/res_ibonds.htm).
- Track tax lots for assets.
- Track portfolio performance
([IRR](https://www.investopedia.com/terms/i/irr.asp)) and cash flows over time.

## Scope and limitations

- **US only.** Taxes, account types and I/EE Bonds follow US rules, and values
are in dollars.
- **Prices come from Yahoo Finance** (via `yfinance`) and Treasury/Vanguard
data. If a source is down or rate limits you, `lak` can't refresh that asset.
- **Tax-loss harvesting is a starting point, not tax advice.** It assumes
specific-lot identification and does not yet check for
[wash sales](https://www.bogleheads.org/wiki/Wash_sale), including purchases
in your other accounts.
- **`lak analyze allocate` is a beta feature.** Sanity check its suggestions
before acting on them.

## Command-line cheat sheet

Run `lak --help` (or add `--help` to any command) for current options. The
[lak user guide](https://sarvjeets.github.io/lakshmi/docs/lak.html) documents
every command in detail.

| To do this | Run |
| --- | --- |
| See assets, totals, allocation and location | `lak list assets total aa al` |
| See tax lots and gains | `lak list lots` |
| Try a hypothetical trade | `lak whatif asset -a VTI -50 asset -a VXUS -t Taxable 50` |
| Decide where new money goes | `lak whatif account -t Taxable 100` then `lak analyze allocate -t Taxable` |
| Check if rebalancing is needed | `lak analyze rebalance` |
| Look for tax-loss harvesting candidates | `lak analyze tlh` |
| Save a checkpoint for performance tracking | `lak add checkpoint` |
| See performance (IRR) | `lak list performance` |

## Library

The `lakshmi` library can also be used directly. The modules and classes are
well documented, and the
[tests](https://github.com/sarvjeets/lakshmi/tree/develop/tests) contain
numerous examples for each method and class.

<details>
<summary>Example: build the example portfolio and print its allocation</summary>

This code constructs the
[example portfolio](https://sarvjeets.github.io/lakshmi/docs/portfolio.yaml)
and prints its asset allocation, asset location and assets:

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
    # portfolio.save('portfolio.yaml')
    print('\n' + portfolio.asset_allocation_compact().string() + '\n')
    print(Table(2, coltypes=['str', 'dollars'])
          .add_row(['Total Assets', portfolio.total_value()]).string())
    print('\n' + portfolio.asset_allocation(['US', 'Intl', 'Bonds']).string())
    print('\n' + portfolio.assets().string() + '\n')
    print(portfolio.asset_location().string())


if __name__ == "__main__":
    main()
```

</details>

## Contributing

Contributions are welcome. All development happens on the `develop` branch.
See [CONTRIBUTING.md](https://github.com/sarvjeets/lakshmi/blob/develop/CONTRIBUTING.md)
for how to set up a development environment, run the tests and submit changes.

## Background

This project is inspired by the [Bogleheads forum](http://bogleheads.org).
Bogleheads focus on a simple but
[powerful philosophy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy)
that allows investors to achieve above-average returns after costs. This tool is
built around the same principles to help an *average* investor manage their
investing portfolio. The
[Bogleheads wiki](https://www.bogleheads.org/wiki/Main_Page) is a great
introduction to basic investing concepts like asset allocation and asset
location.

Lakshmi (meaning "She who leads to one's goal") is one of the principal
goddesses in Hinduism. She is the goddess of wealth, fortune, power, health,
love, beauty, joy and prosperity.

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
