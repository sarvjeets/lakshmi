# Contributing to Lakshmi

As an open-source project, Lakshmi welcomes contributions of any form: bug
reports, documentation fixes, new features, or just feedback from using it.
If you are not sure where to start, see [Good places to start](#good-places-to-start).

## Vision

Lakshmi is very much focussed on the
[Bogleheads philosophy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy).
I would like to keep it simple and as much as possible align with
the teachings of John Bogle and views of the current advisory board over at the
Bogleheads forum. This tool is meant to make investing simpler for the
masses, and discourage harmful practices such as day trading
or speculation. When thinking of new and useful features for Lakshmi,
please consider if it is in line with the Boglehead way of thinking.

Lakshmi is divided into two parts: A core library (`lakshmi`) and simple
interfaces over the core library (currently only `lak` CLI is implemented).
The interfaces themselves are meant to be lightweight wrappers over the core
library, and most of the functionality should be implemented
directly in the library. At some point, it would be nice to add a web &
Android/iOS app interfaces for Lakshmi as well.

&minus; [Sarvjeet](https://github.com/sarvjeets)

## Good places to start

Welcome:

- Bug fixes, and tests for existing behavior.
- New asset types (see [Adding a new asset type](#adding-a-new-asset-type)).
- Making price and data fetching more reliable. Lakshmi depends on
third-party sources (e.g. Yahoo Finance) that change over time.
- Documentation fixes and clarifications, including typos.
- Features that help long-term, buy-and-hold index investors: lowering costs,
staying diversified, tax efficiency, and rebalancing with discipline.

Probably out of scope:

- Anything that encourages trading, market timing, or checking your portfolio
many times a day. (This is why prices are cached for a day.)
- Support for speculative assets or active-trading workflows.
- Features that need your brokerage credentials or send your portfolio data to a
third-party server. Lakshmi is local-first.

If you are unsure whether something fits, open an issue and ask.

## Reporting bugs

Please [open an issue](https://github.com/sarvjeets/lakshmi/issues) and
include:

- The output of `lak --version`, your Python version and your operating
system.
- The exact command you ran and the error. Re-running with `lak --debug ...`
prints the full stack trace.
- A minimal portfolio file that reproduces the problem, when relevant.
**Please do not post your real holdings.** Replace real share counts and
values with made-up numbers, and remove account names or numbers.

## Proposing changes

For small fixes, just send a pull request. For anything non-trivial (a new
command, a change to the portfolio file format, a new dependency), please
open an issue first to discuss the approach. This keeps the discussion public,
prevents wasted effort and makes the pull request easier to review. Draft pull
requests are welcome if you want early feedback.

## Development setup

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

## Adding a new asset type

A new asset type is a good first contribution. Existing assets in
`lakshmi/assets.py` (e.g. `ManualAsset` for the simplest case, `TickerAsset`
for one that fetches prices) are good models to copy. In outline:

1. Subclass `Asset` in `lakshmi/assets.py`. For assets that are held as a
number of shares and can have tax lots, subclass `TradedAsset` instead.
2. Implement the methods the base class requires (`to_dict`, `from_dict`,
`value`, `name` and `short_name`). If the asset fetches data from the
internet, also make it `Cacheable` so that results are cached.
3. Add the class to the `CLASSES` list in `lakshmi/assets.py`. This is what
lets the portfolio file loader and `lak add asset -p <ClassName>` find it.
4. Add a template file named `<ClassName>.yaml` in `lakshmi/data/`. This is the
commented example shown in the editor by `lak add asset` and `lak edit asset`.
5. Add tests in `tests/test_assets.py` (network calls should be mocked).
6. Document the new type in the portfolio file syntax section of
`docs/lak.md`.

## Best practices

- All the development is done on the develop branch. Please fork off your
feature branch from it, and prefer rebases instead of merges to pull new
changes from the upstream branch.
- Please write tests to ensure your new feature or bug fix is tested. Please
run all tests and the pre-submit (see [Development setup](#development-setup))
before sending out the pull request.
- If in doubt, please feel free to open an issue or contact
[me](https://github.com/sarvjeets) over email.
