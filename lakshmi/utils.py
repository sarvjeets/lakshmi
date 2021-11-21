"""Common utils for Lakshmi."""

from datetime import datetime


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


def validate_date(date_text):
    """Validates if the date is in the YYYY/MM/DD format.

    This function either throws a ValueError or returns the date_text
    formatted according to YYYY/MM/DD format.

    Args:
        date_text: Date text to be validated.

    Returns:
        Correctly formatted string representing date_text date.

    Throws:
        ValueError if date is not in YYYY/MM/DD format.
    """
    return datetime.strptime(date_text, '%Y/%m/%d').strftime('%Y/%m/%d')
