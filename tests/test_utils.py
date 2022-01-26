"""Tests for lakshmi.utils module."""
import unittest

from lakshmi import utils


class UtilsTest(unittest.TestCase):
    def test_format_money(self):
        self.assertEqual('$42.42', utils.format_money(42.421))
        self.assertEqual('$100.00', utils.format_money(100.00))

    def test_format_money_delta(self):
        self.assertEqual('+$10.00', utils.format_money_delta(10))
        self.assertEqual('-$20.05', utils.format_money_delta(-20.049))

    def test_validate_date_no_error(self):
        self.assertEqual('2021/11/21', utils.validate_date('2021/11/21'))

    def test_validate_date_corrected(self):
        self.assertEqual('2020/01/01', utils.validate_date('2020/1/1'))

    def test_validate_date_errors(self):
        with self.assertRaises(ValueError):
            utils.validate_date('01/23/2021')

        with self.assertRaises(ValueError):
            utils.validate_date('2021/02/29')  # 2021 is not leap year.
