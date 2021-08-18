"""Common utils for Lakshmi."""


def format_money(x):
    return '${:,.2f}'.format(x)


def format_money_delta(x):
    return '{}${:,.2f}'.format('-' if x < 0 else '+', abs(x))
