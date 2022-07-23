# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Added functionality in `lak list lots` to optionally print account names
and terms for the tax lots.

## Changed
- `lak analyze allocate' now supports asset classes with zero desired ratio.
Thanks [rapidleft](https://github.com/rapidleft).

## [v2.6.0] - 2022-06-21
### Added
- Added functionality in the `cache` module to prefetch multiple cached objects
in parallel threads.
- Added prefetch method in assets that calls the newly added functionality
in the `cache` module. Also, added a prefetch method to portfolio that
prefetches the prices/names for all the assets in the portfolio in parallel.

### Changed
- lak command that access the whole portfolio now uses prefetch to
speed up refreshing the prices of the portfolio by using multiple threads to
do so.

## [v2.5.0] - 2022-04-22
### Added
- A new command `lak analyze allocate` which suggests how to allocate new cash,
while making sure the actual asset allocation remains close to the desired
allocation. This command can also be used to get rebalancing suggestions or to
withdraw money from the portfolio. In all cases, it will suggest changes that
will minimize the relative difference between actual asset allocation and the
desired asset allocation.
- A new
[recipes doc](https://github.com/sarvjeets/lakshmi/blob/develop/docs/recipes.md)
documenting tips and tricks for using Lakshmi.

### Changed
- Changed some of the common methods to return percentages rounded to 1 digit
rather than 0.
- Earlier asset classes with no money mapped to them were not returned when
returning asset allocation. Now all asset classes are returned regardless of
whether they have money mapped or not.

## [v2.4.1] - 2022-02-23
### Fixed
- Relaxed Python requirement to 3.7.

## [v2.4.0] - 2022-02-21
### Added
- A new command `lak list accounts` that allows printing account values and
percentages by accounts or by account types.
### Fixed
- The spinner chars were not showing properly on MS Windows 11. Changed to
a simpler spinner.

## [v2.3.0] - 2022-01-25
### Added
- A new module `lakshmi.performance` that adds ability to checkpoint
portfolio balances and display stats about portfolio's performance over time.
- New commands in `lak` that exposes some functionality of the
`lakshmi.performance` module:
    - `lak add checkpoint`
    - `lak edit checkpoint`
    - `lak delete checkpoint`
    - `lak list checkpoints`
    - `lak list performance`
    - `lak info performance`
- Support in `.lakrc` to specify where the portfolio performance related data
(checkpoints) are stored.
### Fixed
- Help message now shows default values for `lak analyze rebalance`.
- Added validation for I/EE bond purchase dates.

## [v2.2.0] - 2021-11-26
### Added
- [New flag](https://github.com/sarvjeets/lakshmi/blob/develop/docs/lak.md#lakrc)
in `lak` + environment variable support for specifying the `.lakrc` file.
- Changelog (this file).
- Contributing guidelines and development instructions for Lakshmi.
### Changed
- Dependabot is disbled for this project.
- Optimized away unnecessary calls when force refreshing the cached values
(`lak -r` flag).
### Fixed
- Incorrect error handling when `.lakrc` file couldn't be parsed.

## [v2.1.2] - 2021-10-24
### Added
- pre-commit CI now runs for every push and PRs.
### Fixed
- Fix for assets with missing name fields (e.g. 'BTC-USD').
Thanks [bolapara](https://github.com/bolapara).

## [v2.1.1] - 2021-10-22
### Added
- Doc-strings added to all the files.
- Dependabot to auto-update dependencies.
### Fixed
- Documentation.

## [v2.1.0] - 2021-09-06
### Added
- Added pre-commit to the project.
- Support for calling user defined function on cache misses in `lakshmi.cache`.
- Progress bar for slow commands.
- `lak list lots` command.
### Changed
- `lakshmi.lak` module moved from `lakshmi/lak` to `lakshmi/` directory.
- Optimized code to prevent unnecessary calls to slow functions.
### Fixed
- Broken link to `lak.md` from `README.md`.
- User-agent is now set correctly.
- `lak list` warnings for what-ifs are now printed consistently.
- Documentation.

## [v2.0.0] - 2021-08-21
### Added
- Detailed documentation for `lak` command: `docs/lak.md`.
- Integration test for `lak` command.
### Changed
- `lak whatif` and `lak info` command now require a asset or account as a sub-command.
- All function names changed to snake case + PEP8 style formatting.
- Visibility of some members in classes changed to private.
- Short option for --asset-class in `lak list aa` changed from -a to -c (This reduces confusion, -a is used in other commands for specifying asset)
### Fixed
- Language and documentation for `lak` command-line help messages.
- Relax the dependencies to any non-major release of those packages.
- Typos and language in `README.md`.
- Some tests were not running due to duplicate names.

## [v1.0.4] - 2021-08-05
### Fixed
- Moved `data/` files inside lakshmi to include it in wheel package.

## [v1.0.3] - 2021-08-05
### Fixed
- Added `MANIFEST.in` file to include `data/` files in the release package.

## [v1.0.2] - 2021-07-31
### Fixed
- lak add asset command wasn't working due to a typo. Fixed.

## [v1.0.1] - 2021-07-31
### Fixed
- `lak init` command no longer asks user to run lak init first!

## [v1.0.0] - 2021-07-30
### Added
- First release of `lakshmi` library and `lak` tool.
