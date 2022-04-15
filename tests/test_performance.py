"""Test for lakshmi.performance module."""

import unittest
from datetime import datetime

from lakshmi.performance import Checkpoint, Performance, Timeline


class PerformanceTest(unittest.TestCase):

    def test_checkpoint(self):
        c = Checkpoint('2020/11/11', 100)  # Default constructor.
        self.assertEqual(100, c.get_portfolio_value())
        self.assertEqual('2020/11/11', c.get_date())

        c = Checkpoint.from_dict(c.to_dict())
        self.assertEqual(100, c.get_portfolio_value())
        self.assertEqual('2020/11/11', c.get_date())

        c = Checkpoint('2020/1/1', 200, inflow=100, outflow=50)
        self.assertEqual(200, c.get_portfolio_value())
        self.assertEqual('2020/01/01', c.get_date())
        self.assertEqual(100, c.get_inflow())
        self.assertEqual(50, c.get_outflow())

        c = Checkpoint.from_dict(c.to_dict())
        self.assertEqual(200, c.get_portfolio_value())
        self.assertEqual('2020/01/01', c.get_date())
        self.assertEqual(100, c.get_inflow())
        self.assertEqual(50, c.get_outflow())

        self.assertNotIn('Date', c.to_dict(show_date=False))

        c = Checkpoint.from_dict(c.to_dict(show_date=False), '2020/12/12')
        self.assertEqual(200, c.get_portfolio_value())
        self.assertEqual('2020/12/12', c.get_date())
        self.assertEqual(100, c.get_inflow())
        self.assertEqual(50, c.get_outflow())

    def test_show_empty(self):
        c = Checkpoint('2020/11/11', 100, inflow=10)
        d = c.to_dict()
        self.assertFalse('Outflow' in d)
        d = c.to_dict(show_empty_cashflow=True)
        self.assertTrue('Outflow' in d)

    def test_empty_timeline(self):
        with self.assertRaises(AssertionError):
            Timeline([])

    def test_single_entry_timeline(self):
        cp = Checkpoint('2021/1/1', 100.0)
        timeline = Timeline([cp])

        self.assertTrue(timeline.has_checkpoint('2021/01/1'))
        self.assertFalse(timeline.has_checkpoint('2021/01/02'))

        self.assertEqual('2021/01/01', timeline.begin())
        self.assertEqual('2021/01/01', timeline.end())

        self.assertFalse(timeline.covers('2020/12/31'))
        self.assertTrue(timeline.covers('2021/1/1'))

        self.assertEqual(100, timeline.get_checkpoint('2021/01/1')
                         .get_portfolio_value())
        self.assertEqual(100, timeline.get_checkpoint('2021/01/1', True)
                         .get_portfolio_value())
        with self.assertRaises(AssertionError):
            timeline.get_checkpoint('2021/01/02')
        with self.assertRaises(AssertionError):
            timeline.get_checkpoint('2021/01/02', True)

        with self.assertRaises(AssertionError):
            timeline.insert_checkpoint(cp)

        cp_replace = Checkpoint('2021/1/1', 150.0)
        timeline.insert_checkpoint(cp_replace, replace=True)
        self.assertEqual(150, timeline.get_checkpoint('2021/1/1')
                         .get_portfolio_value())

        cp1 = Checkpoint('2020/1/1', 200)
        timeline.insert_checkpoint(cp1)
        self.assertEqual('2020/01/01', timeline.begin())

    def test_timeline(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2021/3/1', 500),
            Checkpoint('2021/1/31', 300, inflow=150, outflow=50)]
        timeline = Timeline(checkpoints)

        self.assertTrue(timeline.has_checkpoint('2021/01/1'))
        self.assertFalse(timeline.has_checkpoint('2021/01/02'))

        self.assertEqual('2021/01/01', timeline.begin())
        self.assertEqual('2021/03/01', timeline.end())

        self.assertFalse(timeline.covers('2020/12/31'))
        self.assertTrue(timeline.covers('2021/1/1'))
        self.assertTrue(timeline.covers('2021/1/2'))
        self.assertTrue(timeline.covers('2021/3/1'))

        self.assertEqual(300, timeline.get_checkpoint('2021/01/31')
                         .get_portfolio_value())
        self.assertEqual(300, timeline.get_checkpoint('2021/01/31', True)
                         .get_portfolio_value())

        with self.assertRaises(AssertionError):
            timeline.get_checkpoint('2021/01/15')

        self.assertEqual(150, timeline.get_checkpoint('2021/01/16', True)
                         .get_portfolio_value())

    def test_timeline_to_list(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2021/3/1', 500),
            Checkpoint('2021/1/31', 300, inflow=150, outflow=50)]
        timeline = Timeline(checkpoints)
        timeline_list = timeline.to_list()
        self.assertEqual([
            {'Date': '2021/01/01', 'Portfolio Value': 100},
            {'Date': '2021/01/31', 'Portfolio Value': 300,
             'Inflow': 150, 'Outflow': 50},
            {'Date': '2021/03/01', 'Portfolio Value': 500}],
            timeline_list)
        timeline = Timeline.from_list(timeline_list)
        self.assertTrue(timeline.has_checkpoint('2021/01/01'))
        self.assertTrue(timeline.has_checkpoint('2021/01/31'))
        self.assertTrue(timeline.has_checkpoint('2021/03/01'))

    def test_timeline_to_table(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2021/3/1', 500),
            Checkpoint('2021/1/31', 300, inflow=150, outflow=50)]
        timeline = Timeline(checkpoints)
        self.assertEqual(
            [['2021/01/01', '$100.00', '$0.00', '$0.00'],
             ['2021/01/31', '$300.00', '$150.00', '$50.00'],
             ['2021/03/01', '$500.00', '$0.00', '$0.00']],
            timeline.to_table().str_list())
        self.assertEqual(
            [['2021/01/01', '$100.00', '$0.00', '$0.00']],
            timeline.to_table('2021/01/01', '2021/01/02').str_list())
        self.assertEqual(
            [['2021/03/01', '$500.00', '$0.00', '$0.00']],
            timeline.to_table('2021/02/01', '2021/04/01').str_list())
        self.assertEqual(
            [['2021/01/31', '$300.00', '$150.00', '$50.00']],
            timeline.to_table('2021/01/31', '2021/01/31').str_list())
        self.assertEqual(
            [], timeline.to_table('2021/01/15', '2021/01/17').str_list())

    def test_get_performance_data(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2021/1/31', 300, inflow=150, outflow=50),
            Checkpoint('2021/3/1', 500, inflow=10, outflow=20)]
        timeline = Timeline(checkpoints)
        data = timeline.get_performance_data('2021/01/01', '2021/03/01')
        self.assertEqual(
            [datetime(2021, 1, 1), datetime(2021, 1, 31),
             datetime(2021, 3, 1)],
            data.dates)
        self.assertEqual([-100, -100, 510], data.amounts)
        self.assertEqual(100, data.begin_balance)
        self.assertEqual(500, data.end_balance)
        self.assertEqual(160, data.inflows)
        self.assertEqual(70, data.outflows)

        data = timeline.get_performance_data('2021/01/16', '2021/01/31')
        self.assertEqual([datetime(2021, 1, 16), datetime(2021, 1, 31)],
                         data.dates)
        self.assertEqual([-150, 200], data.amounts)
        self.assertEqual(150, data.begin_balance)
        self.assertEqual(300, data.end_balance)
        self.assertEqual(150, data.inflows)
        self.assertEqual(50, data.outflows)

    def test_get_performance_data_none_dates(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2021/1/31', 300, inflow=150, outflow=50),
            Checkpoint('2021/3/1', 500, inflow=10, outflow=20)]
        timeline = Timeline(checkpoints)
        data = timeline.get_performance_data(None, None)
        self.assertEqual(100, data.begin_balance)
        self.assertEqual(500, data.end_balance)

    def test_performance_to_dict(self):
        perf = Performance(Timeline([Checkpoint('2021/1/1', 100)]))
        perf = Performance.from_dict(perf.to_dict())
        self.assertEqual('2021/01/01', perf.get_timeline().begin())
        self.assertEqual('2021/01/01', perf.get_timeline().end())

    def test_summary_table_single_date(self):
        perf_table = Performance(Timeline([
            Checkpoint('2021/1/1', 100)])).summary_table()
        self.assertEqual([], perf_table.str_list())

    def test_summary_table_1month(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2021/1/31', 200, inflow=100, outflow=50),
            Checkpoint('2021/2/1', 210)]
        perf = Performance(Timeline(checkpoints))
        # We should only return 1 period.
        self.assertEqual(
            ['1 Month'], perf._get_periods()[1])

        perf_table = perf.summary_table()
        self.assertEqual(2, len(perf_table.list()))
        # Only check basic values (these functions are unittested elsewhere)
        self.assertEqual(['1 Month', '$100.00', '$50.00'],
                         perf_table.str_list()[0][:3])
        self.assertEqual(
            ['Overall', '$100.00', '$50.00', '+$110.00', '110.0%'],
            perf_table.str_list()[1][:5])

    def test_summary_table_1year(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100),
            Checkpoint('2022/2/1', 210)]
        perf = Performance(Timeline(checkpoints))
        self.assertEqual(
            ['3 Months', '6 Months', '1 Year'], perf._get_periods()[1])
        self.assertEqual(4, len(perf.summary_table().list()))

    def test_performance_get_info(self):
        checkpoints = [
            Checkpoint('2020/1/1', 1000),
            Checkpoint('2021/1/1', 500, outflow=1000),
            Checkpoint('2022/1/1', 1000)]
        info = Performance(Timeline(checkpoints)).get_info(None, None)

        self.assertRegex(info, r'Start date +2020/01/01')
        self.assertRegex(info, r'End date +2022/01/01')
        self.assertRegex(info, r'Begin.+ \$1,000.00')
        self.assertRegex(info, r'Ending.+ \$1,000\.00')
        self.assertRegex(info, r'Inflows + \$0')
        self.assertRegex(info, r'Outflows + \$1,000\.00')
        self.assertRegex(info, r'Portfolio growth +\+\$0\.00')
        self.assertRegex(info, r'Market growth +\+\$1,000\.00')
        self.assertRegex(info, r'Portfolio growth \% +0\.0%')
        self.assertRegex(info, r'Internal.+61\.6%')
