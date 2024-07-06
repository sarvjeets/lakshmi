# lak user guide

## Table of Contents

* [Introduction](#introduction)
* [Configuration files and directories](#configuration-files-and-directories)
   * [Portfolio](#portfolio)
   * [Performance](#performance)
   * [Cache](#cache)
   * [lakrc](#lakrc)
* [Portfolio file syntax](#portfolio-file-syntax)
* [Creating a Portfolio](#creating-a-portfolio)
   * [Editing the portfolio file directly](#editing-the-portfolio-file-directly)
   * [Using lak command to create portfolio](#using-lak-command-to-create-portfolio)
* [Help and usage](#help-and-usage)
   * [lak](#lak)
   * [lak init](#lak-init)
   * [lak add](#lak-add)
   * [lak list](#lak-list)
      * [lak list assets](#lak-list-assets)
      * [lak list accounts](#lak-list-accounts)
      * [lak list lots](#lak-list-lots)
      * [lak list total](#lak-list-total)
      * [lak list aa](#lak-list-aa)
      * [lak list al](#lak-list-al)
      * [lak list whatifs](#lak-list-whatifs)
      * [lak list checkpoints](#lak-list-checkpoints)
      * [lak list performance](#lak-list-performance)
   * [lak info](#lak-info)
   * [lak whatif](#lak-whatif)
   * [lak analyze](#lak-analyze)
      * [lak analyze allocate](#lak-analyze-allocate)
      * [lak analyze rebalance](#lak-analyze-rebalance)
      * [lak analyze tlh](#lak-analyze-tlh)
   * [lak edit](#lak-edit)
   * [lak delete](#lak-delete)

## Introduction
lak provides a command-line interface to the lakshmi library. lak is meant
as a tool for managing your investing portfolio. It is inspired by the
[Bogleheads philosophy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy).

[Bogleheads wiki](https://www.bogleheads.org/wiki/Main_Page) is a great
resource for introduction to basic investing concepts like asset allocation,
asset location, etc. The rest of this guide assumes some familiarity with these
investing concepts.

This tool is built for US investors and prints portfolio values in dollars.

## Configuration files and directories

### Portfolio
`lak` stores all the information about accounts, assets, etc. in a portfolio
file. By default, this portfolio is saved in **`~/porfolio.yaml`**. The
[portfolio file syntax](#portfolio-file-syntax) section explains the syntax
of this file. Backing up this file periodically is strongly recommended.

### Performance
The performance related data (checkpoints of the portfolio values, etc.) is
stored in a performance file. By default, this data is stored in
**`~/.perfomance.yaml`**. `lak list performance` and `lak info performance`
commands use this file to compute historical performance stats.

This file is created the first time `lak add checkpoint` is called. Entries
in this file can be added/modified or deleted via the `lak edit checkpoint` and
`lak delete checkpoint` commands.

It is recommended to save portfolio checkpoints periodically (every month or
quarter, or everytime money is added or removed from the portfolio) so that
the performance of the portfolio can be tracked. The tool interpolates the
value of the portfolio between saved checkpoints whenever needed.

### Cache
In addition, `lak` caches the information about the assets in a cache
directory to ensure that subsequent calls to `lak` are fast. By default,
the cache directory is **~/.lakshmicache**. Storing any other file in this
directory is strongly discouraged.

`lak` caches fund/stock/ETF names for a year, stock prices for a day and
the current value of I Bonds and EE Bonds for a month (it refreshes the values
on the 1st of every month).

`lak` cleans up old cached files in this directory when starting up,
and usually it doesn't need any sort of periodic clean-up. The directory and
the files inside it can be safely deleted. The next call to `lak` will
re-create the directory/files, but as expected it would be really slow.

Caching can be permanently disabled using the `.lakrc` file (not recommended)
or you can force `lak` to temporarily refresh cached values by specifying `-r`
or `--refresh` flag to `lak` command:

```
# Reload cached information such as prices etc.
$ lak -r ...
$ lak --refresh ...
```

### lakrc
Both the portfolio file and the cache directory locations can be overridden
by an _optional_ **`~/.lakrc`** file. Like everything else in Lakshmi, this is
a text file in [YAML](http://yaml.org/) format. An example `.lakrc`
file looks like:

```yaml
# Example ~/.lakrc file
# Comments begin with '#' and are ignored.
portfolio: '~/.config/lak/portfolio.yaml'
performance: ~/.config/lak/.performance.yaml
cache: '~/.cache/lakshmicache'
```

Setting the cache to an empty value disables caching (not recommended):

```yaml
# ~/.lakrc file that disables caching (not recommended).
cache:
```

By default `lak` assumes that the config file is located at `~/.lakrc`, but
this location can be overriden by a flag or an environment variable. For
example:

```
# Use lakrc from a different location
$ lak -c ~/.config/lak/.lakrc ...
# The same using environment variable.
$ LAK_CONFIG=~/.config/lak/.lakrc lak ...
```

The config file can also be specified via the `LAK_CONFIG` environment
variable, which can be used instead of repeatedly specifying the config file
via the option. For example, add this to your shell's initialization config
(`.bashrc` or `.zshrc`) to always use an alternate location for your `lakrc`:

```
export LAK_CONFIG=~/.config/lak/.lakrc
```

## Portfolio file syntax
`lak` provides [add](#lak-add) and [edit](#lak-edit) commands to modify
different parts of the portfolio, and these commands present the
user with examples while editing the portfolio. As such, it is better
to rely on those commands instead of directly editing the portfolio file.

The portfolio file is a text file in [YAML](http://yaml.org/) syntax
and consists of only dictionaries and lists.

As a convention, in the format below, _{}_ represents a dictionary and
_[]_ represents a _repeated_ list. Entries that are optional are
surrounded by _<>_.
For example, the
[lakrc](#lakrc) file format can be described as:

```
lakrc := { < 'portfolio': portfolio_filename >,
           < 'cache': cache_directory > }
portfolio_filename := String
cache_directory := < String >
```

[portfolio.yaml](portfolio.yaml) shows an example portfolio file.

The portfolio file syntax is:

```
portfolio := { 'Asset Classes' : asset_class,
               'Accounts' : [ account ] }
asset_class := { 'Name' : String,
                 'Children' : [ asset_class_children ] }
# The 'Ratio' for all children of an asset_class should add up to 1.0
asset_class_children := { 'Ratio' : Float,
                          'Name' : asset_class_name,
                          'Children' : [ asset_class_children ] }
asset_class_name := String

account := { 'Name' : String,
             'Account Type': String,
             'Assets': [ asset ] }

asset := { 'ManualAsset' : manual_asset |
           'TickerAsset' : ticker_asset |
           'VanguardFund' : vanguard_fund_asset |
           'IBonds' : ibond_asset |
           'EEBonds' : eebonds_asset }

manual_asset := { 'Name' : String,
                  'Value' : dollars,
                  'Asset Mapping' : asset_mapping }

dollars := Float

# The floats (ratios) should add up to 1.0
asset_mapping := { asset_class_name : Float,
                   asset_class_name : Float,
                   ... }

ticker_asset := { 'Ticker' : String,
                  'Shares' : Float,
                  'Asset Mapping' : asset_mapping,
                  < 'Tax Lots' : tax_lots > }

tax_lots := [ { 'Date' : date,
               'Quantity' : Float,
               'Unit Cost' : dollars } ]
# Date is specified in YYYY/MM/DD format.
date := String

vanguard_fund_asset := { 'Fund Id' : Integer,
                         'Shares' : Float,
                         'Asset Mapping' : asset_mapping,
                         < 'Tax Lots' : tax_lots > }

ibond_asset := { 'Asset Mapping' : asset_mapping,
                 'Bonds' : [ treasury_bond ] }

treasury_bond := { 'Issue Date' : short_date,
                   'Denomination' : dollars }

eebonds_asset := { 'Asset Mapping' : asset_mapping,
                   'Bonds' : [ treasury_bond ] }
```

* **Asset Classes** are tracked and
presented in the asset allocation view by the `lak list aa` command.
These asset class names are also referred by individual assets to specify
their distribution across these asset classes. Each asset class can be further
sub-divided into asset classes (children) and their respective percentages.
The percentages of children of a particular asset class should add up to
100%. [Example Asset Class section](../lakshmi/data/AssetClass.yaml).
* **Account** represents a collection of assets. The account name could be
anything ('Schwab', 'Vanguard Taxable', 'Her Roth IRA', etc.) but it needs
to be unique across the portfolio. The type of the account is used when
printing the asset location by the `lak list al` command.
[Example Account section](../lakshmi/data/Account.yaml).
* **Asset** represents a particular fund, ETF, a collection of treasury bonds,
etc. Some assets are pre-defined in `lak` and more types of assets can be
added by modifying the `lakshmi.assets` module. Each asset needs to specify
how it maps to the asset classes defined earlier. An asset can map to multiple
asset classes, and the sum of percentages across the asset classes
should add up to 100%.
  * **Manual Asset** is the simplest asset. As the name suggests, this asset
  is tracked manually. The value of this asset needs to be specified and is
  not automatically updated.
  [Example Manual Asset section](../lakshmi/data/ManualAsset.yaml).
  * **Ticker Asset** is any asset that has a ticker symbol (e.g. 'VTI',
  'GOOG', etc.). The value of these assets are automatically pulled from the
  internet and kept up-to date. Tax lots can also be specified and tracked
  for these assets. This is useful for taxable accounts and
  `lak analyze tlh` can notify when/if these tax lots can be
  tax loss harvested.
  [Example Ticker Asset section](../lakshmi/data/TickerAsset.yaml)
  * **Vanguard Fund** are funds that don't have a ticker symbol associated
  with them. Most Vanguard funds do have ticker symbols associated with
  them and as such should be tracked by specifying them as _TickerAsset_.
  An example of such funds are the Institutional funds
  (e.g. 'Vanguard Institutional
  Total Bond Market Index Trust' which has a numeric id, 7555, but not a
  ticker symbol). These funds can also contain tax lot information.
  [Example Vanguard Fund section](../lakshmi/data/VanguardFund.yaml)
  * **I Bonds** and **EE Bonds** are bought and sold electronically at
  [Treasury Direct](https://www.treasurydirect.gov/) or can be purchased
  in paper format via tax refund. This asset tracks value of multiple
  I Bonds or EE Bonds by pulling the current value from the Treasury Direct
  website. If you have a lot of bonds, this could be very slow.
  [Example I Bonds section](../lakshmi/data/IBonds.yaml).
  [Example EE Bonds section](../lakshmi/data/EEBonds.yaml).

## Creating a Portfolio

Most of the commands in `lak` require that a portfolio file already
exists (except `lak init` which creates a new portfolio file). There
are two simple ways of importing your portfolio into `lak`:
1. Use a text editor to create the portfolio file. This might be faster,
but also requires a good understanding of the
[portfolio file syntax](#portfolio-file-syntax). As such, this is not
recommended for most users.
2. Use the `lak init` and `lak add` commands to create
the portfolio. Under the hood, these commands edit parts of the portfolio
file, but provide help and examples relevant to the particular section of
the portfolio being edited.


### Editing the portfolio file directly

To make things easier, it is recommended to copy an
[existing](./portfolio.yaml) file to ~/portfolio.yaml or the location
specified in the [.lakrc](#lakrc) file.
The open up your favorite editor and modify this file using the format
specified in [portfolio file syntax](#portfolio-file-syntax) section.


### Using lak command to create portfolio
This section will run through the process of creating a portfolio file.
Please go through the documentation of
[lak init](#lak-init) and [lak add](#lak-add) commands for more information
on these commands.

The example commands in this section will re-create
[this](./portfolio.yaml) file. While following these examples, please change
the details to match your own portfolio instead of the example one.

#### Step 1: Enter desired Asset allocation
For more information on how to come up your desired asset allocation,
please refer to
[Bogleheads wiki](https://www.bogleheads.org/wiki/Asset_allocation).

For our example, we want to create the following portfolio:

```
All -> Equity 60% and Bonds 40%
Equity -> US 60% and Intl 40%
```

Use the `lak init` command:

```
$ lak init
```
It will open up your default text-editor with:

```yaml
# The asset classes across which to track asset allocation
# (e.g. with lak list aa) command.
# The following shows an example of a nested asset allocation:
# All -> Equity 60% and Bonds 40%
# Equity -> US 60% and Intl 40%
#
# Name of the asset class.
Name: All
# Optionally the children of this asset class (each of which
# is itself an asset class and can have more asset classes
# as children).
Children:
- Ratio: 0.6
  Name: Equity
  Children:
  - Ratio: 0.6
    Name: US
  - Ratio: 0.4
    Name: Intl
- Ratio: 0.4
  Name: Bonds
```

As it turns out the initial example matches our desired asset allocation,
so there is no need to change it. **But, with no changes, `lak init` assumes
the user aborted the edits. Make any minor edit (delete a comment) to accept
this initial file as your portfolio.**
After saving, this creates a new portfolio file.

#### Step 2: Add Accounts
There are three accounts in the [example](./portfolio.yaml) portfolio file.
Let's add them one by one.

```
$ lak add account
```

This opens up an editor with:

```yaml
# An Account represents a collection of Assets (e.g. ETFs or Funds)

# Name of the account, must be unique among all accounts in the portfolio.
Name: Unique-name-for-account

# Type of the account, e.g. Taxable, Tax-Exempt, Tax-Deferred, etc. This
# name is used to group accounts when listing the Asset Location with
# the 'lak list al' command.
Account Type: Tax-Exempt
```

Modify the file to change the account name and type:

```yaml
Name: Schwab Taxable
Account Type: Taxable
```

Re-run the `lak add account` command to add more accounts as needed. In our
case this would mean we will the following accounts:

```
$ lak add account
```

```yaml
# Paste the following lines in the editor.
Name: Roth IRA
Account Type: Tax-Exempt
# Save the file and exit.
```

```
$ lak add account
```

```yaml
# Paste the following lines in the editor.
Name: Vanguard 401(k)
Account Type: Tax-Deferred
# Save the file and exit.
```

Now we are done adding accounts. Let's add some assets to these accounts.

#### Step 3: Add Assets
There are a number of kinds of assets that are supported in _lakshmi_.
Please refer to [portfolio file syntax](#portfolio-file-syntax) section
for a brief description of each of the asset. In our example, we are
just one asset type: TickerAsset.

To add VTI to "Schwab Taxable" account:

```
$ lak add asset -p TickerAsset -t Schwab
```

Note that we just entered "Schwab" instead of the full name as
`lak` commands do a sub-string matching (as long as it can pull up a
unique account or asset with that sub-string).

The command above opens up an editor:

```yaml
# A TickerAsset represents an asset with a ticker symbol. The value of
# these assets can be pulled and updated from the internet (Yahoo Finance).

# The ticker symbol, e.g. 'VTI' or 'VXUS'
Ticker: ITOT

# The number of shares owned.
Shares: 123

# How this asset maps to the asset classes defined in the portfolio.
# This is used to generate asset allocation (e.g. when using
# `lak list aa` command)
Asset Mapping:
  US: 1.0

# Optionally the tax lot information for the asset.
Tax Lots:
- Date: 2020/03/23
  Quantity: 123
  Unit Cost: 50.39
```

Modify the above file to add details for VTI instead:

```yaml
Ticker: VTI
Shares: 1
Asset Mapping:
  US: 1.0
Tax Lots:
- Date: 2021/07/31
  Quantity: 1
  Unit Cost: 226
```

Save and exit the text-editor. It will save the asset in portfolio.
Add other assets to Taxable, Roth and 401(k) accounts:

```
$ lak add asset -p TickerAsset -t Taxable
```

```yaml
# Paste the following lines in the editor.
Ticker: VXUS
Shares: 1
Asset Mapping:
  Intl: 1.0
Tax Lots:
- Date: 2021/07/31
  Quantity: 1
  Unit Cost: 64.94
# Save the file and exit.
```

```
$ lak add asset -p TickerAsset -t Roth
```

```yaml
# Paste the following lines in the editor.
Ticker: VXUS
Shares: 1
Asset Mapping:
  Intl: 1.0
# Save the file and exit.
```

```
$ lak add asset -p TickerAsset -t 401
```

```yaml
# Paste the following lines in the editor.
Ticker: VBMFX
Shares: 20
Asset Mapping:
  Bonds: 1.0
# Save the file and exit.
```

#### Step 4: Verify
Verify the portfolio file was properly created:

```
$ lak list assets
Account          Asset                                                       Value
---------------  --------------------------------------------------------  -------
Schwab Taxable   Vanguard Total Stock Market Index Fund ETF Shares         $228.87
Schwab Taxable   Vanguard Total International Stock Index Fund ETF Shares   $65.46
Roth IRA         Vanguard Total International Stock Index Fund ETF Shares   $65.46
Vanguard 401(k)  Vanguard Total Bond Market Index Fund Investor Shares     $227.60
```

The steps above should create an output similar to this (except the Value
column which depends on the market value of the ETFs added).

## Help and usage

For up to date help, please use the `--help` flag after a command
or sub-command. For example:

```
# Help for lak
$ lak --help

# Help for lak list
$ lak list --help

# Help for lak add asset
$ lak add asset --help
```


### lak

`lak` is the top-level command:

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

The option `--refresh` will force `lak` commands to not used cached
values (See [cache](#cache) for details) and fetch new data from internet.
If your portfolio is large, this will be really slow.

A potential use case would be for fetching the current value of a
TickerAsset (the prices are cached for a day).
In line with boglehead philosophy, it is **strongly recommended** to not
check your portfolio multiple times a day. The decision to cache price
information for a day was partly motivated to reduce the urge to check
your portfolio multiple times a day to see "_how it is doing_".

### lak init

This command is used to create an initial portfolio. Please see
[Using lak command to create portfolio](#using-lak-command-to-create-portfolio)
section for details.

```
$ lak init --help
Usage: lak init [OPTIONS]

  Initializes a new portfolio by adding asset classes. This command can be
  used to create an empty portfolio file if one doesn't exist.

Options:
  --help  Show this message and exit.
```

If you attempt to use `lak init` when a portfolio file exists, it cowardly
refuses to over-write an existing portfolio:

```
$ lak init
Error: Portfolio file already exists: /home/username/portfolio.yaml
```

To resolve this error, please delete the existing portfolio file.


### lak add
This command is used to add accounts, assets or checkpoints:

```
$ lak add --help
Usage: lak add [OPTIONS] COMMAND [ARGS]...

  Add new entities to the portfolio.

Options:
  --help  Show this message and exit.

Commands:
  account     Add a new account to the portfolio.
  asset       Add a new asset to the portfolio.
  checkpoint  Checkpoint the current portfolio value.
```

[Using lak command to create portfolio](#using-lak-command-to-create-portfolio)
provides some examples for this command.

```
$ lak add account --help
Usage: lak add account [OPTIONS]

  Add a new account to the portfolio.

Options:
  --help  Show this message and exit.
```

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

The account names used should be unique across the portfolio. The assets (or
asset names) used inside an Account should be unique, but you can have the
same asset name across accounts.

For information on different asset types, please refer to the list provided in
the [Portfolio file syntax](#portfolio-file-syntax) section.


```
$ lak add checkpoint --help
Usage: lak add checkpoint [OPTIONS]

  Checkpoint the current portfolio value. This creates a new checkpoint for
  today with the current portofolio value (and no cash-flows). To add
  cashflows to this checkpoint, please use the --edit flag.

Options:
  -e, --edit  If set, edit the checkpoint before saving it.
  --help      Show this message and exit.
```

This command checkpoint the current value of the portfolio. This checkpoint
data is saved in the [performance](#performance) file, which is used to
compute historical portfolio performance. If a performance file does not
exist, this command will create a new file. The `--edit` flag can be used to
edit the checkpoint before saving it. This is helpful if you want to add any
cashflows. For example,

```
$ lak add checkpoint --edit
```

This will open your default text-editor with:

```yaml
Portfolio Value: 500.89
Inflow: 0
Outflow: 0

# # Lines starting with "#" are ignored and an empty message aborts this command.

# # The total value of the portfolio (after all the inflows and outflows).
# Portfolio Value: 10_000.00
# # The amount of money added to the portfolio (optional).
# Inflow: 100.00
# # The amount of money withdrawn from the portfolio (optional).
# Outflow: 0
#
```
If any money was added (inflow) or removed (outflow) from the portfolio, those
amounts can be added before the checkpoint is saved. The inflows/outflows are
used to compute the Internal rate of return
([IRR](https://www.investopedia.com/terms/i/irr.asp#:~:text=The%20internal%20rate%20of%20return,a%20discounted%20cash%20flow%20analysis.))
of the portfolio.

The saved checkpoints can listed via `lak list checkpoints` command.
`lak delete chekpoint` and `lak edit checkpoint` can be used to delete or
edit an already saved checkpoint.

### lak list

`lak list` command is used to check on your portfolio's assets, asset
allocation, etc.:

```
$ lak list --help
Usage: lak list [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Command to list various parts of the portfolio.

Options:
  -f, --format [plain|simple|github|grid|fancy_grid|pipe|orgtbl|rst|mediawiki|html|latex|latex_raw|latex_booktabs|latex_longtable|tsv]
                                  Set output table format. For more
                                  information on table formats, please see
                                  "Table format" section on:
                                  https://pypi.org/project/tabulate/
  --help                          Show this message and exit.

Commands:
  aa           Prints the Asset Allocation of the portfolio.
  al           Prints the Asset Location of the portfolio.
  assets       Prints all assets in the portfolio and their current values.
  checkpoints  Prints the portfolio's saved checkpoints.
  lots         Prints tax lot information for all the assets.
  performance  Prints summary stats about portfolio's performance.
  total        Prints the total value of the portfolio.
  whatifs      Prints hypothetical what ifs for assets and accounts.
```

`lak list` command requires a sub-command: `assets`, `total`, `aa`,
`al` or `whatifs`, which are explained in the following sections.

The `lak list` commands can be chained. For example, to print all assets
and the total value of the portfolio:

```
$ lak list assets total
```

The `--format` option is useful for changing the format of the output.
The `lakshmi` library uses [tabulate](https://pypi.org/project/tabulate/)
internally to display tables. A description of all the available format
options can be found in the
[Table format section](https://github.com/astanin/python-tabulate#table-format).
For example, to list assets in a fancy GitHub table format:

```
$ lak list -f github assets
```

| Account         | Asset                                                    |   Value |
|-----------------|----------------------------------------------------------|---------|
| Schwab Taxable  | Vanguard Total Stock Market Index Fund ETF Shares        | $230.00 |
| Schwab Taxable  | Vanguard Total International Stock Index Fund ETF Shares |  $65.93 |
| Roth IRA        | Vanguard Total International Stock Index Fund ETF Shares |  $65.93 |
| Vanguard 401(k) | Vanguard Total Bond Market Index Fund Investor Shares    | $226.80 |


#### lak list assets

This command prints all the assets in the portfolio in a table format.

```
$ lak list assets --help
Usage: lak list assets [OPTIONS]

  Prints all assets in the portfolio and their current values.

Options:
  -s, --short-name  Print the short name of the assets as well (e.g. Ticker
                    for assets that have it).
  -q, --quantity    Print the quantity of the asset (e.g. quantity/shares
                    for assets that have it).
  --help            Show this message and exit.
```

For the portfolio file created previously:

```
$ lak list assets
Account          Asset                                                       Value
---------------  --------------------------------------------------------  -------
Schwab Taxable   Vanguard Total Stock Market Index Fund ETF Shares         $228.87
Schwab Taxable   Vanguard Total International Stock Index Fund ETF Shares   $65.46
Roth IRA         Vanguard Total International Stock Index Fund ETF Shares   $65.46
Vanguard 401(k)  Vanguard Total Bond Market Index Fund Investor Shares     $227.60
```

The Account and Asset columns are self-explanatory. The asset name for
some assets (e.g. `TickerAsset` and `VanguardFund`) is fetched from the
internet and cached for a year. The current value of the asset
is fetched from the internet (except for `ManualAsset`) and cached for a
day.

The short name and quality of the asset can also be printed:

```
$ lak list assets -s -q
Account          Name      Quantity  Asset                                                       Value
---------------  ------  ----------  --------------------------------------------------------  -------
Schwab Taxable   VTI              1  Vanguard Total Stock Market Index Fund ETF Shares         $228.93
Schwab Taxable   VXUS             1  Vanguard Total International Stock Index Fund ETF Shares   $65.59
Roth IRA         VXUS             1  Vanguard Total International Stock Index Fund ETF Shares   $65.59
Vanguard 401(k)  VBMFX           20  Vanguard Total Bond Market Index Fund Investor Shares     $226.80
```

### lak list accounts
This command can be used to print the sum total of value grouped by account
or account types:

```
$ lak list accounts --help
Usage: lak list accounts [OPTIONS]

  Prints all the accounts in the portfolio and their current values.

Options:
  -g, --group  If set, aggregate the account values by account types.
  --help       Show this message and exit.
```

For the portfolio created previously:

```
$ lak list accounts
Account          Account Type      Value    Percentage
---------------  --------------  -------  ------------
Schwab Taxable   Taxable         $280.91           50%
Roth IRA         Tax-Exempt       $61.54           11%
Vanguard 401(k)  Tax-Deferred    $215.00           39%
```

The last columns shows the percentage of value of assets in that account.

The account values can also be aggregated by account types:

```
$ lak list accounts -g
Account Type      Value    Percentage
--------------  -------  ------------
Taxable         $280.91           50%
Tax-Exempt       $61.54           11%
Tax-Deferred    $215.00           39%
```

#### lak list lots

`lak list lots` prints the tax-lots (if specified) for all the assets in the
portfolio. Tax-lots can be specified when adding a new asset
(`lak add asset`), or when editing (`lak edit asset`) a given asset.
To print tax-lots for a single asset, please use `lak info asset` command
instead.

For the portfolio file created previously:

```
$ lak list lots
Short Name    Date           Cost    Gain    Gain%
------------  ----------  -------  ------  -------
VTI           2021/07/31  $226.00  +$8.29       4%
VXUS          2021/07/31   $64.94  +$2.06       3%
```


#### lak list total

`lak list total` prints the total value of the portfolio:

```
$ lak list total --help
Usage: lak list total [OPTIONS]

  Prints the total value of the portfolio.

Options:
  --help  Show this message and exit.
```

For the portfolio file created previously:

```
$ lak list total
------------  -------
Total Assets  $587.39
------------  -------
```

#### lak list aa

`lak list aa` prints the
[asset allocation](https://www.bogleheads.org/wiki/Asset_allocation).
There are a few different formats available:

```
$ lak list aa --help
Usage: lak list aa [OPTIONS]

  Prints the Asset Allocation of the portfolio. For more information, please
  see https://www.bogleheads.org/wiki/Asset_allocation

Options:
  --compact / --no-compact  Print the Asset allocation tree in a vertically
                            compact format  [default: compact]
  -c, --asset-class TEXT    If provided, only print asset allocation for these
                            asset classes. This is a comma separated list of
                            asset classes (not necessarily leaf asset classes)
                            and the allocation across these asset classes
                            should sum to 100%.
  --help                    Show this message and exit.
```

There are three ways to print asset allocation. Let's look at all three
in detail.

1. lak list aa \-\-compact

The default option is to print the asset allocation in _compact_ format. This
view packs the most amount of information in the output:

```
$ lak list aa
Class      A%    D%  Class      A%    D%    Actual%    Desired%    Value    Difference
-------  ----  ----  -------  ----  ----  ---------  ----------  -------  ------------
Equity    61%   60%  US        64%   60%        39%         36%  $230.00       -$18.08
                     Intl      36%   40%        22%         24%  $131.86        +$9.42
Bonds     39%   40%                             39%         40%  $226.80        +$8.66
```

Let's look at each column in detail:
  - *Class*: This column shows the asset classes arranged as a horizontal tree.
  For example, in the output above, there are two asset classes in the
  top-level: _Equity_ and _Bonds_. _Equity_ is further sub-divided into
  _US_ and _Intl_.
  - *A% and D%*: _A%_ and _D%_ stands for Actual percentage and desired
  percentage, respectively. These columns refer to the _Class_ column
  immediately left of them, and shows the ***relative*** percentage of
  those assets in the parent asset class. For example, the columns
  _A%_ right next to _US_ and _Intl_ signifies that the actual
  allocation (based on current balance) of these asset classes is
  _64%_ and _36%_ respectively. The _D%_ column tells us based on the desired
  asset allocation specified for the portfolio, the desired relative
  percentages of these assets should be _60%_ and _40%_.
  - *Actual% and Desired%*: Finally, the last columns show the ***absolute***
  percentages for the leaf asset classes (_US_, _Intl_ and _Bonds_ in the above
  table). These leaf asset classes are the asset classes immediately to the
  left of the values printed in _Actual%_ and _Desired%_ column. Note that the
  _A%_/_D%_ values and the _Actual%_/_Desired%_ values for _US_ and _Intl_ are
  different. This is expected as _A%_ and _D%_ refers to the percentages of
  these assets in _Equity_; however, the _Actual%_ and _Desired%_ refers to the
  percentages of these asset classes in the overall portfolio.
  - *Value and Difference*: Finally, the _Value_ column shows the amount of
  money allocated to the leaf asset class. The _Difference_ column shows how
  far the money allocated is to the desired amount of money allocated. For
  example, the table above shows that if we sold _$18.08_ of _US_ and bought
  _$9.42_ and _$8.66_ of _Intl_ and _Bonds_, we will match the actual
  allocation to the desired allocation perfectly.

The _Difference_ column is an important column to look at, especially when
making or planning (see the [section](#lak-whatif) on `lak whatif`) changes
to the asset allocation. When adding new money, asset classes with the largest
value of _Difference_ should be prioritized and when withdrawing money, the
asset classes with the lowest value of _Difference_ should be prioritized.
Rebalancing can be achieved by just following the current values in this
column (also see `lak analyze rebalance` [section](#lak-analyze)).

2. lak list aa \-\-no-compact

This option still prints asset allocation in a tree format but prints less
information than the default option:

```
$ lak list aa --no-compact
Class      Actual%    Desired%    Value
-------  ---------  ----------  -------
All:
Equity         61%         60%  $361.86
Bonds          39%         40%  $226.80

Equity:
US             64%         60%  $230.00
Intl           36%         40%  $131.86
```

The _Actual%_ and _Desired%_ columns correspond to the ***relative***
allocation of the asset class respective to the parent asset class.
These columns correspond to _A%_ and _D%_ columns in `lak list aa` output.

3. lak list aa \-\-asset-class

This command print's asset allocation, but only across the asset classes
explicitly mentioned in the `--asset-class` flag. For example:

```
$ lak list aa --asset-class US,Intl,Bonds
Class      Actual%    Desired%    Value    Difference
-------  ---------  ----------  -------  ------------
US             39%         36%  $230.00       -$18.08
Intl           22%         24%  $131.86        +$9.42
Bonds          39%         40%  $226.80        +$8.66

# Space in the asset class list requires quotes around them.
$ lak list aa --asset-class 'Equity, Bonds'
Class      Actual%    Desired%    Value    Difference
-------  ---------  ----------  -------  ------------
Equity         61%         60%  $361.86        -$8.66
Bonds          39%         40%  $226.80        +$8.66
```

The column meaning is similar to the default output of `lak list aa` command
(explained above).

It is important to ensure that the asset classes specified completely
_cover_ the allocation in the portfolio, without any overlap. Here are
some examples that will throw an error (`AssetAllocation called with
overlapping Asset Classes or Asset Classes which does not cover the
full tree.`):
  - `lak list aa --asset-class Equity,US`: Overlapping asset classes.
  - `lak list aa --asset-class US, Intl`: The list doesn't cover _Bonds_.

#### lak list al
This command prints the asset location across the types of accounts.
The information is important to ensure that assets are placed
[efficiently](https://www.bogleheads.org/wiki/Tax-efficient_fund_placement)
across accounts.

```
$ lak list al
Asset Class    Account Type      Percentage    Value
-------------  --------------  ------------  -------
US             Taxable                 100%  $230.00
Intl           Taxable                  50%   $65.93
               Tax-Exempt               50%   $65.93
Bonds          Tax-Deferred            100%  $226.80
```

The _percentage_ refers to the percentage of the asset class printed
in the first column across account types. Please see `lak whatif`
[section](#lak-whatif) as well.

#### lak list whatifs

When `lak whatif` [command](#lak-whatif) is used to test out hypothetical
changes to the portfolio, `lak list whatifs` lists all the hypothetical
changes made to the portfolio. If there are no changes, the output is empty.
For example:

```
$ lak list whatifs
# Empty output as no whatifs are set.

# Hypothetically move $10 from VTI to VXUS in the taxable account.
$ lak whatif asset -a 'VTI' -10 asset -a 'VXUS' -t 'Tax' 10

$ lak list whatifs
Account         Asset                                                       Delta
--------------  --------------------------------------------------------  -------
Schwab Taxable  Vanguard Total Stock Market Index Fund ETF Shares         -$10.00
Schwab Taxable  Vanguard Total International Stock Index Fund ETF Shares  +$10.00
```

#### lak list checkpoints

This command lists all the checkpoints that were saved for a portfolio (e.g.
by using the `lak add checkpoint` command).

```
$ lak list checkpoints --help
Usage: lak list checkpoints [OPTIONS]

  Prints the portfolio's saved checkpoints.

Options:
  -b, --begin DATE  Start printing the checkpoints from this date (Format:
                    YYYY/MM/DD). If not provided, defaults to earliest date
                    for which a checkpoint exists.
  -e, --end DATE    Stop printing the checkpoints at this date (Format:
                    YYYY/MM/DD). If not provided, defaults to the latest date
                    for which a checkpoint exists.
  --help            Show this message and exit.
```

A sample output for this command looks like:

```
$ lak list checkpoints
Date          Portfolio Value    Inflow    Outflow
----------  -----------------  --------  ---------
2021/01/03            $550.00     $0.00      $0.00
2021/12/08            $587.39    $10.00    $100.00
2022/01/22            $564.89     $0.00      $0.00
```

In addition to the portfolio value, this command lists the inflows (money
added to the portfolio) or outflows (money removed from the portfolio) on
different dates.

#### lak list performance

This command is used to print information about portfolio performance based
on the checkpoints that were previously saved. A sample output for this
command looks like:

```
$ lak list performance
Period      Inflows    Outflows    Portfolio Change    Change %    IRR
--------  ---------  ----------  ------------------  ----------  -----
3 Months     $10.00     $100.00             -$95.59        -14%    -4%
6 Months     $10.00     $100.00             -$61.77        -10%    10%
1 Year       $10.00     $100.00              +$7.75          1%    18%
Overall      $10.00     $100.00             +$14.89          3%    18%
```

This command lists the portfolio inflows and outflows, change in the portfolio
value and performance stats for different time periods. The
last column
([IRR](https://www.investopedia.com/terms/i/irr.asp#:~:text=The%20internal%20rate%20of%20return,a%20discounted%20cash%20flow%20analysis.))
refers to the Internal Rate of Return of the portfolio.

### lak info

This command is useful to print detailed information about parts of the
portfolio (e.g. account or asset). Here are few examples:

```
$ lak info --help
Usage: lak info [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Print detailed information about parts of the portfolio.

Options:
  --help  Show this message and exit.

Commands:
  account      Print details of an account.
  asset        Print details of an asset.
  performance  Print detailed stats about portfolio's performance.

$ lak info account --help
Usage: lak info account [OPTIONS]

  Print details of an account.

Options:
  -t, --account substr  Print info about the account that matches this
                        substring  [required]
  --help                Show this message and exit.

# Don't need to list the whole name, as long as substr matches a unique account.
$ lak info account -t Sch
Name:   Schwab Taxable
Type:   Taxable
Total:  $295.93

$ lak info asset --help
Usage: lak info asset [OPTIONS]

  Print details of an asset.

Options:
  -a, --asset substr    Print info about the asset that matches this substring
                        [required]
  -t, --account substr  If the asset name is not unique across the portfolio,
                        an optional substring to specify the account to which
                        the asset belongs.
  --help                Show this message and exit.

# The short name of an asset can also be specified.
$ lak info asset -a VTI
Ticker:               VTI
Name:                 Vanguard Total Stock Market Index Fund ETF Shares
Asset Class Mapping:  US  100%
Value:                $230.00
Price:                $230.00

Tax lots:
Date          Quantity     Cost    Gain    Gain%
----------  ---------  -------  ------  -------
2021/07/31          1  $226.00  +$4.00       2%

# It can also match a part of the full asset name as long as it is unique
$ lak info asset -a 'Total Sto'
Ticker:               VTI
Name:                 Vanguard Total Stock Market Index Fund ETF Shares
Asset Class Mapping:  US  100%
Value:                $230.00
Price:                $230.00

Tax lots:
Date          Quantity     Cost    Gain    Gain%
----------  ---------  -------  ------  -------
2021/07/31          1  $226.00  +$4.00       2%

# If the asset is not unique across the portfolio, the account name
# has to be specified.
$ lak info asset -a VXUS -t Schwab
Ticker:               VXUS
Name:                 Vanguard Total International Stock Index Fund ETF Shares
Asset Class Mapping:  Intl  100%
Value:                $65.93
Price:                $65.93

Tax lots:
Date          Quantity    Cost    Gain    Gain%
----------  ---------  ------  ------  -------
2021/07/31          1  $64.94  +$0.99       2%
```

If the portfolio has saved checkpoints (created via the `lak add checkpoint`
command), `lak info performance` can be used to print
detailed stats about the perfolio's performance for different time periods:

```
$ lak info performance --help
Usage: lak info performance [OPTIONS]

  Print detailed stats about portfolio's performance.

Options:
  -b, --begin DATE  Begining date from which to start computing performance
                    stats (Format: YYYY/MM/DD). If not provided, defaults to
                    the earliest possible date.
  -e, --end DATE    Ending date at which to stop computing performance stats
                    (Format: YYYY/MM/DD). If not provided, defaults to today.
  --help            Show this message and exit.

# If there is no checkpoint for the date specified, the value of the portfolio
# on that date is simply interpolated based on the two checkpoints surrounding
# it.

$ lak info performance -b 2021/06/06
Start date               2021/06/06
End date                 2022/01/22
Beginning balance        $607.87
Ending balance           $564.89
Inflows                  $10.00
Outflows                 $100.00
Portfolio growth         -$42.98
Market growth            +$47.02
Portfolio growth %       -7%
Internal Rate of Return  13%
```

Just like the `lak list` command, `lak info` command can be chained:

```
$ lak info asset -a 'VTI' asset -a 'VBMFX'
Ticker:               VTI
Name:                 Vanguard Total Stock Market Index Fund ETF Shares
Asset Class Mapping:  US  100%
Value:                $230.00
Price:                $230.00

Tax lots:
Date          Quantity     Cost    Gain    Gain%
----------  ---------  -------  ------  -------
2021/07/31          1  $226.00  +$4.00       2%

Ticker:               VBMFX
Name:                 Vanguard Total Bond Market Index Fund Investor Shares
Asset Class Mapping:  Bonds  100%
Value:                $226.80
Price:                $11.34
```

### lak whatif

This command is useful to run hypothetical whatif scenarios on a
portfolio without actually making those changes. After specifying
the changes via the `lak whatif` command, all the `lak` commands
(`lak list aa`, `lak list al`, etc.)
behave as if those changes were _actually_ made to the portfolio.
To warn the user, some commands print a warning at the top indicating
that hypothetical whatifs are set.

These whatifs are ignored for the purposes of creating and saving checkpoints
(e.g. with `lak add checkpoint`).

Just the like the `lak info` command, `lak whatif` command take either
`account` or `asset` as a sub-command:

```
$ lak whatif --help
Usage: lak whatif [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Run hypothetical what if scenarios by modifying the total value of an
  account or asset. This is useful to see how the asset allocation or location
  will change if you make these changes. Once you are done playing around with
  the hypothetical changes, you can reset them all by using the --reset flag.

Options:
  -r, --reset  Reset all hypothetical whatif amounts.
  --help       Show this message and exit.

Commands:
  account  Run hypothetical what if scenario on an account.
  asset    Run hypothetical what if scenario on an asset.
```

To see what happens to the asset allocation if we sell _$50_ worth of VTI:

```
$ lak list aa --asset-class US,Intl,Bonds
Class      Actual%    Desired%    Value    Difference
-------  ---------  ----------  -------  ------------
US             39%         36%  $230.00       -$18.08
Intl           22%         24%  $131.86        +$9.42
Bonds          39%         40%  $226.80        +$8.66

$ lak whatif asset -a VTI -50

$ lak list aa --asset-class US,Intl,Bonds
Warning: Hypothetical what ifs are set.

Class      Actual%    Desired%    Value    Difference
-------  ---------  ----------  -------  ------------
US             33%         36%  $180.00       +$13.92
Intl           24%         24%  $131.86        -$2.58
Bonds          42%         40%  $226.80       -$11.34
```

We see that the actual allocation of _US_ asset class decreased from
_39%_ to _33%_ with those changes. Note the warning on top of the second
`lak list aa` command.

`lak list whatifs` can be used to check which whatifs are set:

```
$ lak list whatifs
Account            Cash
--------------  -------
Schwab Taxable  +$50.00

Account         Asset                                                Delta
--------------  -------------------------------------------------  -------
Schwab Taxable  Vanguard Total Stock Market Index Fund ETF Shares  -$50.00
```

We see that selling _$50_ worth of _VTI_ didn't remove the money from the
portfolio. It simply shows up in the account as extra cash (so `lak list total`
will not show any difference in the total value of the portfolio).

`lak whatif account` can be used to remove the extra cash from the
portfolio:

```
$ lak whatif account -t Schwab -50
$ lak list whatifs
Account         Asset                                                Delta
--------------  -------------------------------------------------  -------
Schwab Taxable  Vanguard Total Stock Market Index Fund ETF Shares  -$50.00
```

`lak whatif -r` is a shortcut to reset and delete all whatif that are set.

This command can be chained to specify multiple `whatif` commands. For example,
to reset all existing whatifs and move _$50_ from _VTI_ to _VXUS_:

```
$ lak whatif -r asset -a VTI -50 asset -a VXUS -t Taxable 50
$ lak list whatifs
Account         Asset                                                       Delta
--------------  --------------------------------------------------------  -------
Schwab Taxable  Vanguard Total Stock Market Index Fund ETF Shares         -$50.00
Schwab Taxable  Vanguard Total International Stock Index Fund ETF Shares  +$50.00
```

### lak analyze

This command is used to analyze the portfolio:

```
$ lak analyze --help
Usage: lak analyze [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Analyze the portfolio.

Options:
  --help  Show this message and exit.

Commands:
  allocate   Allocates any unallocated cash in an account to assets.
  rebalance  Shows if any asset classes need to be rebalanced based on a...
  tlh        Shows which tax lots can be Tax-loss harvested (TLH).
```

#### lak analyze allocate

```
$ lak analyze allocate --help
Usage: lak analyze allocate [OPTIONS]

  Allocates any unallocated cash in an account to assets. If an account has
  any unallocated cash (aka what if) then this command allocates that cash to
  the assets in the account. This allocation is done with the goal of
  minimizing the relative ratio of actual allocation to the desired ratio of
  asset classes.

  The unallocated cash in the account could be negative in which cash money is
  removed from the assets.

  This command modifies the portfolio by applying the resulting deltas to it
  (similar to `lak whatif` command).

  WARNING: This is a BETA feature and is subject to change or be removed.
  Always sanity check the suggestions before acting on them.

Options:
  -t, --account substr       Allocate any cash in the account that matches
                             this substring.  [required]
  -e, --exclude-assets TEXT  If provided, these assets in the account are not
                             allocated any cash. This is a comma separated
                             list of assets specified by their short names.
  -r, --rebalance            If not set (the default), money is either only
                             added (in case the acccount has any unallocated
                             cash) or only removed (in case the account has
                             negative unallocated cash) from the assets. If
                             set, money is both added and removed (as needed)
                             from the assets to minimize the relative
                             difference from the desired asset allocation.
  --help                     Show this message and exit.
```

As an example, let's consider the example portfolio:

```
$ lak list assets aa
Account          Asset                                                       Value
---------------  --------------------------------------------------------  -------
Schwab Taxable   Vanguard Total Stock Market Index Fund ETF Shares         $214.22
Schwab Taxable   Vanguard Total International Stock Index Fund ETF Shares   $57.01
Roth IRA         Vanguard Total International Stock Index Fund ETF Shares   $57.01
Vanguard 401(k)  Vanguard Total Bond Market Index Fund Investor Shares     $201.20

Class      A%    D%  Class      A%    D%    Actual%    Desired%    Value    Difference
-------  ----  ----  -------  ----  ----  ---------  ----------  -------  ------------
Equity    62%   60%  US        65%   60%        40%         36%  $214.22       -$23.62
                     Intl      35%   40%        22%         24%  $114.02       +$13.05
Bonds     38%   40%                             38%         40%  $201.20       +$10.58
```

Let's assume we wanted to invest an extra $20 in the `Schwab Taxable` account
and wanted to know which asset to allocate the cash to. Let's first tell
`lakshmi` that we have extra cash in an account:

```
$ lak whatif account -t 'Taxable' 20
```

After that we can ask it to allocate the cash:

```
$ lak analyze allocate -t 'Taxable'
Asset      Delta
-------  -------
VTI       +$0.00
VXUS     +$20.00

$ lak list whatifs aa
Account         Asset                                                       Delta
--------------  --------------------------------------------------------  -------
Schwab Taxable  Vanguard Total International Stock Index Fund ETF Shares  +$20.00

Class      A%    D%  Class      A%    D%    Actual%    Desired%    Value    Difference
-------  ----  ----  -------  ----  ----  ---------  ----------  -------  ------------
Equity    63%   60%  US        62%   60%        39%         36%  $214.22       -$16.42
                     Intl      38%   40%        24%         24%  $134.02        -$2.15
Bonds     37%   40%                             37%         40%  $201.20       +$18.58

# Let's reset the whatifs
$ lak whatif -r
```

We can also use the same command to see how to rebalance within an account.
Let's asssume we wanted to rebalance the portfolio by only selling & buying
assets in the Schwab account. (This is a made up example. In most cases,
one would want to avoid rebalancing in a taxable account. A better account to
rebalance would be a 401(K) or Roth as there are no tax consequences for
doing so.)

```
$ lak list aa
Class      A%    D%  Class      A%    D%    Actual%    Desired%    Value    Difference
-------  ----  ----  -------  ----  ----  ---------  ----------  -------  ------------
Equity    62%   60%  US        65%   60%        40%         36%  $214.22       -$23.62
                     Intl      35%   40%        22%         24%  $114.02       +$13.05
Bonds     38%   40%                             38%         40%  $201.20       +$10.58

$ lak analyze allocate -t 'Taxable' -r
Asset      Delta
-------  -------
VTI      -$16.30
VXUS     +$16.30

$ lak list aa
Warning: Hypothetical what ifs are set.

Class      A%    D%  Class      A%    D%    Actual%    Desired%    Value    Difference
-------  ----  ----  -------  ----  ----  ---------  ----------  -------  ------------
Equity    62%   60%  US        60%   60%        37%         36%  $197.92        -$7.32
                     Intl      40%   40%        25%         24%  $130.32        -$3.25
Bonds     38%   40%                             38%         40%  $201.20       +$10.58
```

#### lak analyze rebalance

```
$ lak analyze rebalance --help
Usage: lak analyze rebalance [OPTIONS]

  Shows if any asset classes need to be rebalanced based on a band based
  rebalancing scheme. For more information, please refer to
  https://www.whitecoatinvestor.com/rebalancing-the-525-rule/.

Options:
  -a, --max-abs-percentage FLOAT  Max absolute difference before rebalancing.
                                  [default: 5]
  -r, --max-relative-percentage FLOAT
                                  The max relative difference before
                                  rebalancing.  [default: 25]
  --help                          Show this message and exit.
```

The `rebalance` command only shows asset classes that don't fall within
the rebalancing bands. If all asset classes are within the bands, it prints
a message to that effect:

```
$ lak analyze rebalance
Portfolio Asset allocation within bounds.
```

#### lak analyze tlh

```
$ lak analyze tlh --help
Usage: lak analyze tlh [OPTIONS]

  Shows which tax lots can be Tax-loss harvested (TLH).

Options:
  -p, --max-percentage FLOAT  The max percentage loss for each lot before
                              TLHing.  [default: 10]
  -d, --max-dollars INTEGER   The max absolute loss for an asset (across all
                              tax lots) before TLHing.
  --help                      Show this message and exit.
```

**A word of caution about the `tlh` command**: This command assumes that
specific share identification is picked as the investing accounting
method. Currently, it also doesn't account for
[wash sales](https://www.bogleheads.org/wiki/Wash_sale), which could
be problematic. Taxation is a complex topic and users are _strongly_
advised to do their own research before using this tool.

### lak edit

This command is used to edit various parts of the portfolio. The
[portfolio](#portfolio) or the [performance](#performance) file can be
directly edited if so desired,
but `lak edit` makes it easier to directly modify the relevant
parts of the portfolio file.

```
$ lak edit --help
Usage: lak edit [OPTIONS] COMMAND [ARGS]...

  Edit parts of the portfolio.

Options:
  --help  Show this message and exit.

Commands:
  account     Edit an account in the portfolio.
  asset       Edit an asset in the portfolio.
  assetclass  Edit the Asset classes and the desired asset allocation.
  checkpoint  Edit a protfolio's checkpoint.
```

For example, to edit the Schwab taxable account:

```
$ lak edit account -t Taxable
```

This opens up an editor with:

```
Name: Schwab Taxable
Account Type: Taxable


# # Lines starting with "#" are ignored and an empty message aborts this command.

# # An Account represents a collection of Assets (e.g. ETFs or Funds)
#
# # Name of the account, must be unique among all accounts in the portfolio.
# Name: Unique-name-for-account
#
# # Type of the account, e.g. Taxable, Tax-Exempt, Tax-Deferred, etc. This
# # name is used to group accounts when listing the Asset Location with
# # the 'lak list al' command.
# Account Type: Tax-Exempt
#
```

Every `lak edit` sub-commands prints a similar (commented out) help message
at the bottom.

If no edits are made or an empty message is provided (i.e. by deleting
all the lines), the command is aborted. If there are any errors in the
file, `lak edit` prints the error, and prompts the user to re-edit the
file.

`lak edit checkpoint` command is used to edit previously saved checkpoints or
to add new checkpoint in-between two saved checkpoints. This is useful for
adding new information (e.g. missing cashflows) retroactively to the portfolio.
For example,
```
$ lak list checkpoints
Date          Portfolio Value    Inflow    Outflow
----------  -----------------  --------  ---------
2021/01/03            $550.00     $0.00      $0.00
2021/12/08            $587.39    $10.00    $100.00
2022/01/22            $564.89     $0.00      $0.00

$ lak edit checkpoint -d 2021/11/11
# This will open up editor with checkpoint for date 2021/11/11 with the
# portfolio value pre-filled for that checkpoint by interpolating the portfolio
# values from 2021/01/03 and 2021/12/08.
```

### lak delete

This command allows the user to delete accounts, assets or checkpoints from
the portfolio:

```
$ lak delete --help
Usage: lak delete [OPTIONS] COMMAND [ARGS]...

  Delete different entities from the portfolio.

Options:
  --help  Show this message and exit.

Commands:
  account     Delete an account from the portfolio.
  asset       Delete an asset from the portfolio.
  checkpoint  Delete checkpoint for a given date.
```

`lak delete` sub-commands prompt the user to confirm if they want to delete
the specified entity before actually deleting it. This can be skipped via
the `--yes` flag.
