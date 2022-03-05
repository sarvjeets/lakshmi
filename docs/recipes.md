# Lakshmi Recipes

## Table of Contents

* [Introduction](#introduction)
* [Clean-up config files](#clean-up-config-files)
* [Turn on auto-completion](#turn-on-auto-completion)
* [Manage multiple portfolios](#manage-multiple-portfolios)
* [Setting up automatic emails](#setting-up-automatic-emails)
* [How to reorder list of accounts or assets](#how-to-reorder-list-of-accounts-or-assets)

## Introduction
This document goes through some suggestions, tips and tricks for
using the `lak` tool. For detailed help on the `lak` tool, please
see the [lak user guide](./lak.md).

## Clean-up config files
The default locations of the lak config files are in the user home directory.
This clutters up the home directory, and many users would prefer to move these
files elsewhere. `lak` supports overriding these defaults. For linux-based
systems, it is recommended that the config files are moved to `~/.config/lak`
directory and the cache is moved to `~/.cache/lakshmicache`.

Here are the steps. First move the config files and cache (if some of these
files don't exist, you can safely ignore them):

```shell
mkdir -p ~/.config/lak
mkdir -p ~/.cache
# Move all the config files to .config/lak
mv ~/portfolio.yaml ~/.performance.yaml ~/.lakrc ~/.config/lak
# Move cache to .cache
mv ~/.lakshmicache ~/.cache/lakshmicache
```

Now modify `lakrc` to point to new configuration directories. Edit
`~/.config/lak/.lakrc` and replace the existing paths with new paths:

```
portfolio: '~/.config/lak/portfolio.yaml'
performance: ~/.config/lak/.performance.yaml
cache: '~/.cache/lakshmicache'
```

Finally, make sure `lak` is reading its config from the new file. In your
shell configuration file (e.g. `.bashrc` for Bash or `.zshrc` for Zsh),
add the following line:

```shell
export LAK_CONFIG=~/.config/lak/.lakrc
```

## Turn on auto-completion

`lak` is built on top of `click` which supports
[shell completion](https://click.palletsprojects.com/en/8.0.x/shell-completion)
for Bash, Zsh and Fish shells. Shell completion suggests command names, option
names, etc.

Completion can be enabled by invoking `lak` during start-up for every shell
session, but this is slow. The recommended method is to generate a config
file once and source that into shell of your choice.

For Bash:

```shell
_LAK_COMPLETE=bash_source lak > ~/.config/.lak-complete.bash

# Source the file in ~/.bashrc.
. ~/.config/lak-complete.bash
```

For Zsh:

```shell
_LAK_COMPLETE=zsh_souce lak > ~/.config/.lak-complete.zsh

# Source the file in ~/.zshrc.
. ~/.config/lak-complete.zsh
```

For Fish:

```shell
# Save the script to ~/.config/fish/completions/lak.fish:
_LAK_COMPLETE=fish_source lak > ~/.config/fish/completions/lak.fish
```

## Manage multiple portfolios

Many times users will find themselves managing multiple independent portfolios.
The recommended way for doing this is to create multiple `lak` config files,
each pointing to a difference portfolio file (and optionally a perfomance
file if checkpointing is used). For example:

```
# ~/.config/lak/lakrc1
portfolio: '~/.config/lak/portfolio1.yaml'
performance: ~/.config/lak/.performance1.yaml
cache: '~/.cache/lakshmicache' # This can be shared.
```

```
# ~/.config/lak/lakrc2
portfolio: '~/.config/lak/portfolio2.yaml'
performance: ~/.config/lak/.performance2.yaml
cache: '~/.cache/lakshmicache' # This can be shared.
```

```
# ~/.config/lak/lakrc3
portfolio: '~/.config/lak/portfolio3.yaml'
performance: ~/.config/lak/.performance3.yaml
cache: '~/.cache/lakshmicache' # This can be shared.
```

Then you can create aliases in your shell config file (`.bashrc` for bash or
`.zshrc` for Zsh):

```shell
alias lak1='LAK_CONFIG=~/.config/lak/.lakrc1 lak'
alias lak2='LAK_CONFIG=~/.config/lak/.lakrc2 lak'
alias lak3='LAK_CONFIG=~/.config/lak/.lakrc3 lak'
```

After this, `lak1` command can be used to manage portfolio 1 and so on.

## Setting up automatic emails

One of the benefits of using `lak` is that users can automate a lot of
portfolio monitoring tasks. Instead of accessing your portfolio through
the `lak` tool manually, users can create a script to send them emails
periodically. For example, below is a shell script to send an HTML email
about the portfolio status:

```shell
#!/bin/bash

EMAIL=YOUR_EMAIL_HERE@DOMAIN.com
PATH=PATH_TO_LAK_TOOL:$PATH

# This depends on the ssmtp tool. You can replace this with your installed
# email program.
cat << EMAIL_END | ssmtp $EMAIL
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8
To:${EMAIL}
Subject: Portfolio Update

<html>
<head>
  <style>
    table, th, td {
      border: 2px solid black;
      border-collapse: collapse;
      padding: 6px;
    }
  </style>
</head>
<body>

<h2>tl:dr;</h2>
<pre>
$(lak analyze tlh -p 10 -d 20000 rebalance)
</pre>

<br><hr><br>

<h2>Asset Allocation</h2>
$(lak list -f html aa -c 'US,Intl,Bonds')

<br>

$(lak list -f html total)

<br><hr><br>

<h2>Assets</h2>
$(lak list -f html assets)

<br><hr><br>

<h2>Tax lots</h2>
$(lak list -f html lots)

<h2>Performance</h2>
$(lak list -f html performance)

</body>
</html>
EMAIL_END
```

A scheduling program like [cron](ttps://wiki.archlinux.org/title/cron) can be
used to run this script periodically. For example, to send this monthly on 5th
at 5am:
```
# Entry for lak in crontab:
00 05 5 * * portfolio_email.sh
```
## How to reorder list of accounts or assets
There is currently no automated way to re-order list of accounts or assets
appearing in `lak list accounts` or `lak list assets`. But the
[portfolio file](./lak.md#portfolio) can be manually edited and different
sections can be moved around to achieve this. Please see
[Portfolio file syntax](./lak.md#portfolio-file-syntax) for help on the syntax
of this file.
