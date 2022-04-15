"""This module contains all classes and functions related to checkpointing
and computing portfolio's performance."""

import bisect
from dataclasses import dataclass
from datetime import datetime, timedelta

import yaml
from pyxirr import xirr

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

        assert portfolio_value > 0, 'Portfolio value must be positive'
        assert inflow >= 0, 'Inflow must be non-negative'
        assert outflow >= 0, 'Outflow must be non-negative'

        # Round portfolio value to 2 degits.
        self._portfolio_value = round(portfolio_value, 2)
        self._inflow = inflow
        self._outflow = outflow

    def to_dict(self, show_empty_cashflow=False, show_date=True):
        """Converts this object to a dictionary.

        Args:
            show_empty_cashflow: If set to True, inflows and outflows are
            shown even if they are empty.
            show_date: If set to False, date is not included in the dictionary
            output.

        Returns:
            A dictionary object representing this object.
        """
        d = {}
        if show_date:
            d['Date'] = self._date
        d['Portfolio Value'] = self._portfolio_value
        if show_empty_cashflow or self._inflow > 0:
            d['Inflow'] = self._inflow
        if show_empty_cashflow or self._outflow > 0:
            d['Outflow'] = self._outflow
        return d

    @classmethod
    def from_dict(cls, d, date=None):
        """Returns a new object given dictionary representation.

        This function is reverse of the above function. Optionally, it takes
        in a date which is used to set the date if it is specified. If it is
        not specified than this function expects that a data is specified via
        d. This is a reverse function of to_dict().

        Args:
            d: A dictionary representing this object (usually a output of
            to_dict method).
            date: Date for this checkpoint (Format: YYYY/MM/DD).

        Returns: A newly initialized object of type Checkpoint.

        Raises:
            AssertionError if the dictionary format is not as expected.
        """
        if not date:
            date = d.pop('Date')
        ret_obj = Checkpoint(date, d.pop('Portfolio Value'),
                             d.pop('Inflow', 0), d.pop('Outflow', 0))
        assert len(d) == 0, f'Extra attributes found while parsing: {list(d)}'
        return ret_obj

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
                f'Cannot have two checkpoints with the same date ({cp_date})')
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

    def to_table(self, begin=None, end=None):
        """Convert this timeline to a Table.

        This function is useful for pretty-printing this object.

        Args:
            begin: If specified, start printing checkpoints from this date
            (inclusive). Format: 'YYYY/MM/DD'. If None, start from the earliest
            checkpoint date.
            end: If specified, stop printing checkpoints after this date
            (inclusive). Format: 'YYYY/MM/DD'. If None, end at the last
            checkpoint date.

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

    def insert_checkpoint(self, checkpoint, replace=False):
        """Inserts given checkpoint to the timeline.

        Args:
            checkpoint: Checkpoint to insert.
            replace: If True, the new checkpoint overwrites a checkpoint with
            the same date present in the timeline.

        Raises:
            AssertionError if replace is False and another checkpoint with the
            same date is present in the timeline.
        """
        date = checkpoint.get_date()

        if replace and self.has_checkpoint(date):
            self._checkpoints[date] = checkpoint
            return

        assert not self.has_checkpoint(date), (
            f'Cannot insert two checkpoints with the same date ({date}).')
        pos = bisect.bisect(self._dates, date)
        self._dates.insert(pos, date)
        self._checkpoints[date] = checkpoint

    def delete_checkpoint(self, date):
        """Removes checkpoint corresponding to date."""
        date = utils.validate_date(date)
        assert date in self._checkpoints
        self._checkpoints.pop(date)
        self._dates.remove(date)

    @dataclass
    class PerformanceData:
        # List of dates (datetime objects). Used to compute XIRR.
        dates: list
        # List of cashflows on the above dates. Money flowing out of portfolio
        # is considered positive. Used to compute XIRR.
        amounts: list
        # Beginning balance.
        begin_balance: float
        # Ending balance.
        end_balance: float
        # Sum of all inflows to the portfolio.
        inflows: float = 0.0
        # Sum of all outflows from the portfolio.
        outflows: float = 0.0

    def get_performance_data(self, begin, end):
        """Returns data in a format to help calculate XIRR.

        Args:
            begin: Begin date in YYYY/MM/DD format. If None, start from the
            earliest checkpoint date.
            end: End date in YYYY/MM/DD format. If None, ends at the last
            checkpoint date.

        Returns: PerformanceData object.
        """
        if not begin:
            begin = self.begin()
        if not end:
            end = self.end()

        assert utils.validate_date(begin) != utils.validate_date(end)

        dates = []
        amounts = []
        inflows = 0.0
        outflows = 0.0

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
            inflows += checkpoint.get_inflow()
            outflows += checkpoint.get_outflow()

        end_checkpoint = self.get_checkpoint(end, True)
        dates.append(
            datetime.strptime(end_checkpoint.get_date(), Timeline._DATE_FMT))
        amounts.append(end_checkpoint.get_portfolio_value()
                       + end_checkpoint.get_outflow()
                       - end_checkpoint.get_inflow())
        inflows += end_checkpoint.get_inflow()
        outflows += end_checkpoint.get_outflow()
        return Timeline.PerformanceData(
            dates=dates, amounts=amounts, inflows=inflows, outflows=outflows,
            begin_balance=begin_checkpoint.get_portfolio_value(),
            end_balance=end_checkpoint.get_portfolio_value())


class Performance:
    """Class to compute performance stats given a Timeline object."""

    _TIME_PERIODS = [timedelta(days=30),
                     timedelta(days=30) * 3,
                     timedelta(days=30) * 6,
                     timedelta(days=365),
                     timedelta(days=365) * 3,
                     timedelta(days=365) * 10]
    _TIME_PERIODS_NAMES = ['1 Month',
                           '3 Months',
                           '6 Months',
                           '1 Year',
                           '3 Years',
                           '10 Years']

    def __init__(self, timeline):
        self._timeline = timeline

    def get_timeline(self):
        """Returns the timeline."""
        return self._timeline

    def to_dict(self):
        """Converts this object to a dictionary."""
        return {'Timeline': self._timeline.to_list()}

    @classmethod
    def from_dict(cls, d):
        """Creates a new Performance object from a dict (reverse of above)."""
        ret_obj = Performance(Timeline.from_list(d.pop('Timeline')))
        assert len(d) == 0, f'Extra attributes found: {list(d.keys())}'
        return ret_obj

    def save(self, filename):
        """Save this Object to a file."""
        with open(filename, 'w') as f:
            yaml.dump(self.to_dict(), f)

    @classmethod
    def load(cls, filename):
        """Load Performance object from a file."""
        with open(filename) as f:
            return Performance.from_dict(
                yaml.load(f.read(), Loader=yaml.SafeLoader))

    def _get_periods(self):
        """Returns periods for which summary stats should be printed."""
        # We only show 3 _TIME_PERIODS based on timeline_period
        timeline_period = (
            datetime.strptime(self._timeline.end(), Timeline._DATE_FMT)
            - datetime.strptime(self._timeline.begin(), Timeline._DATE_FMT))
        end_index = bisect.bisect_left(Performance._TIME_PERIODS,
                                       timeline_period)
        begin_index = max(0, end_index - 3)
        return (Performance._TIME_PERIODS[begin_index:end_index],
                Performance._TIME_PERIODS_NAMES[begin_index:end_index])

    @classmethod
    def _create_summary_row(cls, period_name, perf_data):
        """Helper method to create a row in summary table."""
        change = perf_data.end_balance - perf_data.begin_balance
        return [period_name, perf_data.inflows, perf_data.outflows,
                change, change / perf_data.begin_balance,
                xirr(perf_data.dates, perf_data.amounts)]

    def summary_table(self):
        """Returns summary of performance during different periods."""
        table = Table(6,
                      headers=['Period', 'Inflows', 'Outflows',
                               'Portfolio Change', 'Change %', 'IRR'],
                      coltypes=['str', 'dollars', 'dollars', 'delta_dollars',
                                'percentage_1', 'percentage_1'])
        # Not enough data for any points.
        if self._timeline.begin() == self._timeline.end():
            return table

        # Add rows for atmost 3 periods.
        periods, period_names = self._get_periods()
        for period, period_name in zip(periods, period_names):
            begin_date_str = (
                datetime.strptime(self._timeline.end(), Timeline._DATE_FMT)
                - period).strftime(Timeline._DATE_FMT)
            table.add_row(Performance._create_summary_row(
                period_name, self._timeline.get_performance_data(
                    begin_date_str, self._timeline.end())))

        # Add row for 'Overall' time period
        table.add_row(Performance._create_summary_row(
            'Overall', self._timeline.get_performance_data(
                self._timeline.begin(), self._timeline.end())))
        return table

    def get_info(self, begin, end):
        """Get information about the performance in [begin, end].

        This method prints detailed information about performance of portfolio
        (as given by checkpoints).

        Args:
            begin: Begin date in YYYY/MM/DD format. If None, starts at the
            earliest checkpoint date.
            end: End date in YYYY/MM/DD format. If None, ends at the last
            checkpoint date.

        Returns: A formatted string suitable for pretty-printing.
        """
        # Make dates strings cannonical.
        begin = utils.validate_date(begin) if begin else self._timeline.begin()
        end = utils.validate_date(end) if end else self._timeline.end()
        if begin == end:
            # Not enought checkpoints to compute performance.
            return ''

        data = self._timeline.get_performance_data(begin, end)
        change = data.end_balance - data.begin_balance

        table = Table(2, coltypes=['str', 'str'])
        growth = round(100 * change / data.begin_balance, 1)
        irr = round(100 * xirr(data.dates, data.amounts), 1)
        table.set_rows([
            ['Start date', begin],
            ['End date', end],
            ['Beginning balance', utils.format_money(data.begin_balance)],
            ['Ending balance', utils.format_money(data.end_balance)],
            ['Inflows', utils.format_money(data.inflows)],
            ['Outflows', utils.format_money(data.outflows)],
            ['Portfolio growth', utils.format_money_delta(change)],
            ['Market growth', utils.format_money_delta(
                change - data.inflows + data.outflows)],
            ['Portfolio growth %', f'{growth}%'],
            ['Internal Rate of Return', f'{irr}%']])
        return table.string(tablefmt='plain')
