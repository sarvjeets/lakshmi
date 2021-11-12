"""Test for lakshmi.performance module."""

import unittest

from lakshmi.performance import Checkpoint


class PerformanceTest(unittest.TestCase):

    def test_checkpoint(self):
        c1 = Checkpoint(100)  # Default constructor.
        self.assertEquals(100, c1.get_portfolio_value())
        c = Checkpoint(200, '2020-11-11')
        self.assertEquals(200, c.get_portfolio_value())
        self.assertEquals('2020-11-11', c.get_date())

        c.merge(c1)
        self.assertEquals(200, c.get_portfolio_value())
        self.assertEquals('2020-11-11', c.get_date())
