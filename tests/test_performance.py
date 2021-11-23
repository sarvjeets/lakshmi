"""Test for lakshmi.performance module."""

import unittest

from lakshmi.performance import Checkpoint, Timeline


class PerformanceTest(unittest.TestCase):

    def test_checkpoint(self):
        c = Checkpoint('2020/11/11', 100)  # Default constructor.
        self.assertEqual(100, c.get_portfolio_value())
        self.assertEqual('2020/11/11', c.get_date())

        c = Checkpoint('2020/1/1', 200, inflow=100, outflow=50)
        self.assertEqual(200, c.get_portfolio_value())
        self.assertEqual('2020/01/01', c.get_date())
        self.assertEqual(100, c.get_inflow())
        self.assertEqual(50, c.get_outflow())

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

        cp1 = Checkpoint('2020/1/1', 200)
        timeline.insert_checkpoint(cp1)
        self.assertEqual('2020/01/01', timeline.begin())

    def test_timeline(self):
        checkpoints = [
            Checkpoint('2021/1/1', 100), Checkpoint('2021/3/1', 500),
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
