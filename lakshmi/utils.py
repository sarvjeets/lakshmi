"""Common utils for Lakshmi."""

def FormatMoney(x):
    return '${:,.2f}'.format(x)

def FormatMoneyDelta(x):
    return '{}${:,.2f}'.format('-' if x < 0 else '+', abs(x))
