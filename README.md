# Lakshmi

## Introduction
This project is inspired by all the time I spent on
[Bogleheads forum](bogleheads.org). The forum taught me to focus on important
things like asset allocation, location and minimizing costs. The focus is on
simple but [powerful philosophy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy)
that allows investors to acheive above-average
returns (after costs). This tool is build around the same priciples to help
an _average_ investor manage their investing portfolio.

## Installation

You can install the package via pip:
```
pip install lakshmi
```

## Command-line interface

(This is a quick-start guide. You may find a detailed description of
the tool [here](add_link))

The simplest way to use this project is via the **lak** command. You may
access upto date help via:

```
lak --help
```

You may create a new portfolio by either:
1. Copying an [existing](TODO) portfolio file to ~/portfolio.yaml and editing
it.

-- OR --

2. You may do it step-by-step via the lak commands. The following command will
open up an editor to enter your desired asset allocation:
```
lak init
```

You can also view help for any of the commands. For example, to view help for
the init command:
```
lak init --help
```

You may add few accounts (His/Her 401(k), Roth IRAs, Taxable, etc.) via
the **lak add** command:
```
lak add account
```
After that you can add assets to these accounts via:
```
lak add asset -p TickerAsset -t account_str
```

That's it. Now you can view you portfolio, asset allocation and asset location via:
```
lak list assets total aa al
```

[TODO: Detailed Description of the tool](todo)

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
