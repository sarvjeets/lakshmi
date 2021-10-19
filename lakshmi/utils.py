"""Common utils for Lakshmi."""


def format_money(x):
    """Formats input (money) to a string.

    For example, if x=5.238, the output is '$5.24'.

    Args:
        x: Float (non-negative) representing dollars.
    """
    return '${:,.2f}'.format(x)


def format_money_delta(x):
    """Formats input (money delta) into a string.

    For example, if x=-23.249m the output is '-$23.25'.

    Args:
        x: Float (postive or negative) representating dollars.
    """
    return '{}${:,.2f}'.format('-' if x < 0 else '+', abs(x))
