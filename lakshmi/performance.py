"""This module contains all classes and functions related to checkpointing
and computing portfolio's performance."""

import bisect
from datetime import datetime

import yaml

from lakshmi import utils
from lakshmi.table import Table


class Checkpoint:
    """Class representing a single checkpoint of the portfolio. Each checkpoint
    represents a single day. The checkpoint contains the portfolio value, and
    money inflows and outflows on that day.
    """

    def __init__(self, checkpoint_date, portfolio_value, inflow=0, outflow=0):
        """Constructs a new checkpoint for the given date.

        Args:
            checkpoint_date: Date in 'YYYY/MM/DD' format.
            portfolio_value: The value of the portfolio on that date.
            inflow: The amount of money flowing into the portfolio on date.
            outflow: The amount of money flowing out of the portfolio on date.
        """
        self._date = utils.validate_date(checkpoint_date)

        assert portfolio_value >= 0, 'Portfolio value must be non-negative'
        assert inflow >= 0, 'Inflow must be non-negative'
        assert outflow >= 0, 'Outflow must be non-negative'

        self._portfolio_value = portfolio_value
        self._inflow = inflow
        self._outflow = outflow

    def to_dict(self, show_empty_cashflow=False):
        """Converts this object to a dictionary.

        Args:
            show_empty_cashflow: If set to True, inflows and outflows are
            shown even if they are empty.
        """
        d = {}
        d['Date'] = self._date
        d['Portfolio Value'] = self._portfolio_value
        if show_empty_cashflow or self._inflow > 0:
            d['Inflow'] = self._inflow
        if show_empty_cashflow or self._outflow > 0:
            d['Outflow'] = self._outflow
        return d

    @classmethod
    def from_dict(cls, d):
        """Returns a new object given dictionary representation d."""
        keys = set(d.keys())
        keys.difference_update(
            {'Date', 'Portfolio Value', 'Inflow', 'Outflow'})
        assert len(keys) == 0, f'Extra attributes found while parsing: {keys}'
        return Checkpoint(d.get('Date'), d.get('Portfolio Value'),
                          d.get('Inflow', 0), d.get('Outflow', 0))

    def get_date(self):
        """Returns date of this checkpoint in 'YYYY/MM/DD' format."""
        return self._date

    def get_portfolio_value(self):
        """Returns the checkpoint's portfolio value."""
        return self._portfolio_value

    def get_inflow(self):
        """Returns the money flowing in."""
        return self._inflow

    def get_outflow(self):
        """Returns the money flowing out."""
        return self._outflow


class Timeline:
    """Class representing a collection of checkpoints."""

    _DATE_FMT = '%Y/%m/%d'

    def __init__(self, checkpoints):
        """Returns a new object given a list of checkpoints."""
        assert len(checkpoints) > 0

        self._checkpoints = {}
        self._dates = []
        for cp in checkpoints:
            cp_date = cp.get_date()
            assert cp_date not in self._dates, (
                'Cannot have two checkpoints with the same date')
            self._dates.append(cp_date)
            self._checkpoints[cp_date] = cp
        self._dates.sort()

    def to_list(self):
        """Returns this object as a list of checkpoints."""
        return [self._checkpoints[date].to_dict() for date in self._dates]

    @classmethod
    def from_list(cls, timeline_list):
        """Returns a new object given a list (reverse of method above)."""
        return Timeline([Checkpoint.from_dict(cp) for cp in timeline_list])

    def save(self, filename):
        """Save this Timeline to a file."""
        with open(filename, 'w') as f:
            yaml.dump(self.to_list(), f)

    @classmethod
    def load(cls, filename):
        """Load Timeline from a file."""
        with open(filename) as f:
            return Timeline.from_list(
                yaml.load(f.read(), Loader=yaml.SafeLoader))

    def to_table(self, begin=None, end=None):
        """Convert this timeline to a Table.

        This function is useful for pretty-printing this object.

        Args:
            begin: If specified, start printing checkpoints from this date
            (inclusive). Format: 'YYYY/MM/DD'.
            end: If specified, stop printing checkpoints after this date
            (inclusive). Format: 'YYYY/MM/DD'.

        Returns: A lakshmi.table.Table object.
        """
        table = Table(4,
                      headers=['Date', 'Portfolio Value', 'Inflow', 'Outflow'],
                      coltypes=['str', 'dollars', 'dollars', 'dollars'])
        begin_pos = bisect.bisect_left(self._dates, begin) if begin else None
        end_pos = bisect.bisect_right(self._dates, end) if end else None
        for date in self._dates[begin_pos:end_pos]:
            cp = self._checkpoints[date]
            table.add_row([cp.get_date(),
                           cp.get_portfolio_value(),
                           cp.get_inflow(),
                           cp.get_outflow()])
        return table

    def has_checkpoint(self, date):
        """Retuns true iff there is a checkpoint for date."""
        return utils.validate_date(date) in self._checkpoints

    def begin(self):
        """Returns the beginnning date of this timeline."""
        return self._dates[0]

    def end(self):
        """Returns the end date of this timeline."""
        return self._dates[-1]

    def covers(self, date):
        """Returns true if date is within the timeline."""
        date = utils.validate_date(date)
        return (date >= self.begin() and date <= self.end())

    @classmethod
    def _interpolate_checkpoint(cls, date, checkpoint1, checkpoint2):
        """Given checkpoints 1 and 2, returns new checkpoint for date."""
        date1 = datetime.strptime(checkpoint1.get_date(), Timeline._DATE_FMT)
        date2 = datetime.strptime(checkpoint2.get_date(), Timeline._DATE_FMT)
        given_date = datetime.strptime(date, Timeline._DATE_FMT)
        val1 = checkpoint1.get_portfolio_value()
        val2 = (checkpoint2.get_portfolio_value()
                - checkpoint2.get_inflow()
                + checkpoint2.get_outflow())

        interpolated_value = val1 + (val2 - val1) * (
            (given_date - date1) / (date2 - date1))
        return Checkpoint(date, interpolated_value)

    def get_checkpoint(self, date, interpolate=False):
        """Returns checkpoint for a given date.

        This function will return the checkpoint for date if it already exists
        in the Timeline. If there is no checkpoint for date, this function
        throws an error if interpolate is False. If interpolate is set to True
        this function will linearly interpolate the portfolio values around
        the given date and return a newly created checkpoint with that
        calculated value.

        Args:
            date: The date (in 'YYYY/MM/DD' format) for which to return the
            checkpoint.
            interpolate: If True, computes and returns a checkpoint for a date
            even if one doesn't exists in the Timeline.
        Returns:
            Checkpoint object corresponding to date.
        Raises:
            AssertionError, if interpolate is False and there is no checkpoint
            for date.
            AssertError, If date is not without the range of checkpoints in
            this timeline.
        """
        date = utils.validate_date(date)

        if self.has_checkpoint(date):
            return self._checkpoints[date]

        # date is not one of the saved checkpoints...

        assert interpolate, f'{date} is not one of the saved checkpoints.'

        # ... and it's OK to interpolate

        assert self.covers(date), (
            f'{date} is not in the range of the saved checkpoints. '
            f'Begin={self.begin()}, End={self.end()}')

        pos = bisect.bisect(self._dates, date)
        return Timeline._interpolate_checkpoint(
            date,
            self._checkpoints[self._dates[pos - 1]],
            self._checkpoints[self._dates[pos]])

    def insert_checkpoint(self, checkpoint):
        """Inserts checkpoint to the timeline."""
        date = checkpoint.get_date()
        assert not self.has_checkpoint(date), (
            'Cannot insert two checkpoints with the same date.')
        pos = bisect.bisect(self._dates, date)
        self._dates.insert(pos, date)
        self._checkpoints[date] = checkpoint

    def delete_checkpoint(self, date):
        """Removes checkpoint corresponding to date."""
        date = utils.validate_date(date)
        assert date in self._checkpoints
        self._checkpoints.pop(date)
        self._dates.remove(date)

    def get_xirr_data(self, begin, end):
        """Returns data in a format to help calculate XIRR.

        Args:
            begin: Begin date in YYYY/MM/DD format.
            end: End date in YYYY/MM/DD format.

        Returns: (dates, amounts) where both lists has the same size. dates
        contain the dates of the cashflows and amounts contains the
        consolidated cashflows on those dates (money flowing out of the
        portfolio is positive).
        """
        dates = []
        amounts = []

        begin_checkpoint = self.get_checkpoint(begin, True)
        dates.append(datetime.strptime(begin_checkpoint.get_date(),
                                       Timeline._DATE_FMT))
        amounts.append(-begin_checkpoint.get_portfolio_value())

        begin_pos = bisect.bisect_right(self._dates, begin)
        end_pos = bisect.bisect_left(self._dates, end)
        for date in self._dates[begin_pos:end_pos]:
            dates.append(datetime.strptime(date, Timeline._DATE_FMT))
            checkpoint = self._checkpoints[date]
            amounts.append(checkpoint.get_outflow() - checkpoint.get_inflow())

        end_checkpoint = self.get_checkpoint(end, True)
        dates.append(
            datetime.strptime(end_checkpoint.get_date(), Timeline._DATE_FMT))
        amounts.append(end_checkpoint.get_portfolio_value()
                       + end_checkpoint.get_outflow()
                       - end_checkpoint.get_inflow())
        return dates, amounts


class Performance:
    """Class to compute portfolio's performance."""
    pass
