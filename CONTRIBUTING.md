# Contributing to Lakshmi

As an open-source project, Lakshmi welcomes contributions of any form.
Some examples of how you can contribute:

- Fix or add documentation.
- Improve code quality and readability.
- Find and report any bugs. Even better fix them!
- Send requests for features that you would like to see in lakshmi.
- Implement new features that you would like to see in Lakshmi. Please see
the [section](#vision) below for some direction on what kind of features
would be a good addition to Lakshmi. A running list of features and ideas is
also available at the [projects](https://github.com/sarvjeets/lakshmi/projects)
page.
- Last but not least, please use it, send feedback and share it with others.

## Vision

Lakshmi is very much focussed on the
[Bogleheads philosopy](https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy).
I would like to keep it simple and as much as possible align with
the teachings of John Bogle and views of the current advisory board over at the
Bogleheads forum. This tool is meant to make investing simpler for the
masses, and discourage harmful practices such as day trading
or speculatiion. When thinking of new and useful features for Lakshmi,
please consider if it is inline with the Boglehead way of thinking.

Lakshmi is divided into two parts: A core library (`lakshmi`) and simple
interfaces over the core library (currently only `lak` CLI is implemented).
The interfaces themselves are meant to be lightweight wrappers over the core
library, and most of the functionality should be implemented
directly in the library. At some point, it would be nice to add a web &
Andriod/iOS app interfaces for Lakshmi as well.

&minus; [Sarvjeet](https://github.com/sarvjeets)

## Best practices
- Please read up the Development section in the [README](./README.md) file.
- All the development is done on the develop branch. Please fork off your
feature branch from it, and prefer rebases instead of merges to pull new
changes from the upstream branch.
- Please write tests to ensure your new feature or bug fix is tested. Please
run all tests and the pre-submit before sending out the pull request.
- When reporting a bug, please list the contents of your .lakrc and portfolio
file whenever relevant.
- If you are planning to work on a non-trivial feature, please discuss
the implementation over email or with a shared Google document. This will
prevent wasted time and effort on your part and will make the pull requests
easier to review.
- If in doubt, please feel free to contact [me](https://github.com/sarvjeets)
over email first.
