"""Tests for lakshmi.table module."""
from lakshmi.table import Table
import unittest


class TableTest(unittest.TestCase):
    def test_empty_table(self):
        t = Table(3)
        self.assertListEqual([], t.List())
        self.assertListEqual([], t.StrList())
        self.assertEqual('', t.String())

    def test_no_headers_and_coltypes(self):
        t = Table(3)
        t.AddRow(['1', '2', '3'])
        self.assertListEqual([['1', '2', '3']],
                             t.List())
        self.assertListEqual([['1', '2', '3']],
                             t.StrList())
        self.assertGreater(len(t.String()), 0)

    def test_bad_coltypes(self):
        with self.assertRaisesRegex(AssertionError, 'Bad column type in coltypes'):
            Table(2, coltypes=[None, 'str'])

    def test_set_rows(self):
        t = Table(3)
        t.SetRows([['1', '2']])
        self.assertListEqual([['1', '2']], t.StrList())

    def test_headers_and_diff_coltypes(self):
        headers = ['1', '2', '3', '4', '5']
        t = Table(
            5,
            headers=headers,
            coltypes=['str', 'dollars', 'delta_dollars', 'percentage', 'float'])

        rows = [['r1', 3, 4.1, 0.5, 1],
                ['r6', 8, -9.2, 0.1, 2.345]]
        t.SetRows(rows)

        self.assertListEqual(headers, t.Headers())
        self.assertListEqual(
            ['left', 'right', 'right', 'right', 'decimal'],
            t.ColAlign())

        self.assertListEqual(rows, t.List())
        self.assertListEqual(
            [['r1', '$3.00', '+$4.10', '50%', '1.0'],
             ['r6', '$8.00', '-$9.20', '10%', '2.345']],
            t.StrList())
        self.assertGreater(len(t.String()), 0)

    def test_mismatched_num_cols(self):
        with self.assertRaises(AssertionError):
            t = Table(2, headers=['1'])
        with self.assertRaises(AssertionError):
            t = Table(2, headers=['1', '2', '3'])
        with self.assertRaises(AssertionError):
            t = Table(2, coltypes=['str'])
        with self.assertRaises(AssertionError):
            t = Table(2, headers=['str', 'str', 'str'])

    def test_too_many_cols(self):
        t = Table(2)
        with self.assertRaises(AssertionError):
            t.AddRow(['1', '2', '3'])
        with self.assertRaises(AssertionError):
            t.SetRows([['a', 'b'],
                       ['1', '2', '3']])

    def test_too_few_cols(self):
        t = Table(2)
        t.AddRow(['1'])
        t.SetRows([['1', '2'], ['1'], ['a']])


if __name__ == '__main__':
    unittest.main()
