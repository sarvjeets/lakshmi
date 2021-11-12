"""This module contains all classes and functions related to checkpointing
and computing portfolio's performance."""

from datetime import date


class Checkpoint:
    """Class representing a single checkpoint of the portfolio."""

    def __init__(self, portfolio_value,
                 checkpoint_date=date.today().isoformat()):
        """Constructs a new checkpoint for the given date.

        Args:
            checkpoint_date: Date in 'YYYY-MM-DD' format.
            portfolio_value: The current value of the portfolio.
        """
        self._date = checkpoint_date
        assert portfolio_value >= 0.0
        self._portfolio_value = portfolio_value

    def get_date(self):
        """Returns date of this checkpoint in "YYYY-MM-DD" format."""
        return self._date

    def get_portfolio_value(self):
        """Returns the checkpoint's portfolio value."""
        return self._portfolio_value

    def merge(self, other):
        """Returns a checkpoint by merging other into this object."""
        # Right now this doesn't do much.
        return self


class Timeline:
    """Class representing a collection of checkpoints."""

    def __init__(self, checkpoints=[]):
        """Returns a new object given a list of checkpoints."""
        self._checkpoints = checkpoints
        # TODO: Do some validation.

    def return_checkpoints(self, begin=None, end=None):
        """Return all the checkpoints between begin and end."""
        pass


class Performance:
    """Class to compute portfolio's performance."""
    pass
