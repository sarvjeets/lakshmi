"""Tests for lakshmi.table module."""
from lakshmi.table import Table
import unittest


class TableTest(unittest.TestCase):
    def testEmptyTable(self):
        t = Table(3)
        self.assertListEqual([], t.List())
        self.assertListEqual([], t.StrList())
        self.assertEqual('', t.String())

    def testNoHeadersAndColTypes(self):
        t = Table(3)
        t.AddRow(['1', '2', '3'])
        self.assertListEqual([['1', '2', '3']],
                             t.List())
        self.assertListEqual([['1', '2', '3']],
                             t.StrList())
        self.assertGreater(len(t.String()), 0)

    def testBadColType(self):
        with self.assertRaisesRegex(AssertionError, 'Bad column type in coltypes'):
            Table(2, coltypes=[None, 'str'])

    def testSetRows(self):
        t = Table(3)
        t.SetRows([['1', '2']])
        self.assertListEqual([['1', '2']], t.StrList())

    def testHeadersAndDiffColTypes(self):
        headers = ['1', '2', '3', '4']
        t = Table(
            4,
            headers=headers,
            coltypes=['str', 'dollars', 'delta_dollars', 'percentage'])

        rows = [['r1', 3, 4.1, 0.5],
                ['r6', 8, -9.2, 0.1]]
        t.SetRows(rows)

        self.assertListEqual(headers, t.Headers())
        self.assertListEqual(
            ['left', 'right', 'right', 'left'],
            t.ColAlign())

        self.assertListEqual(rows, t.List())
        self.assertListEqual(
            [['r1', '$3.00', '+$4.10', '50%'],
             ['r6', '$8.00', '-$9.20', '10%']],
            t.StrList())
        self.assertGreater(len(t.String()), 0)

    def testMismatchedNumCols(self):
        with self.assertRaises(AssertionError):
            t = Table(2, headers=['1'])
        with self.assertRaises(AssertionError):
            t = Table(2, headers=['1', '2', '3'])
        with self.assertRaises(AssertionError):
            t = Table(2, coltypes=['str'])
        with self.assertRaises(AssertionError):
            t = Table(2, headers=['str', 'str', 'str'])

    def testTooManyCols(self):
        t = Table(2)
        with self.assertRaises(AssertionError):
            t.AddRow(['1', '2', '3'])
        with self.assertRaises(AssertionError):
            t.SetRows([['a', 'b'],
                       ['1', '2', '3']])

    def testTooFewCols(self):
        t = Table(2)
        t.AddRow(['1'])
        t.SetRows([['1', '2'], ['1'], ['a']])


if __name__ == '__main__':
    unittest.main()
