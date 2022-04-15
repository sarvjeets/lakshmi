"""Tests for lakshmi.table module."""
import unittest

from lakshmi.table import Table


class TableTest(unittest.TestCase):
    def test_sanity(self):
        self.assertEqual(len(Table.coltype2func), len(Table.coltype2align))

    def test_empty_table(self):
        t = Table(3)
        self.assertListEqual([], t.list())
        self.assertListEqual([], t.str_list())
        self.assertEqual('', t.string())

    def test_no_headers_and_coltypes(self):
        t = Table(3)
        t.add_row(['1', '2', '3'])
        self.assertListEqual([['1', '2', '3']], t.list())
        self.assertListEqual([['1', '2', '3']], t.str_list())
        self.assertGreater(len(t.string()), 0)

    def test_bad_coltypes(self):
        with self.assertRaisesRegex(AssertionError,
                                    'Bad column type in coltypes'):
            Table(2, coltypes=[None, 'str'])

    def test_set_rows(self):
        t = Table(3)
        t.set_rows([['1', '2']])
        self.assertListEqual([['1', '2']], t.str_list())

    def test_headers_and_diff_coltypes(self):
        headers = ['1', '2', '3', '4', '5', '6']
        t = Table(
            6,
            headers=headers,
            coltypes=[
                'str',
                'dollars',
                'delta_dollars',
                'percentage',
                'percentage_1',
                'float'])

        rows = [['r1', 3, 4.1, 0.5, 0.5, 1],
                ['r6', 8, -9.2, 0.1, 0.5557, 2.345]]
        t.set_rows(rows)

        self.assertListEqual(headers, t.headers())
        self.assertListEqual(
            ['left', 'right', 'right', 'right', 'right', 'decimal'],
            t.col_align())

        self.assertListEqual(rows, t.list())
        self.assertListEqual(
            [['r1', '$3.00', '+$4.10', '50%', '50.0%', '1.0'],
             ['r6', '$8.00', '-$9.20', '10%', '55.6%', '2.345']],
            t.str_list())
        self.assertGreater(len(t.string()), 0)

    def test_mismatched_num_cols(self):
        with self.assertRaises(AssertionError):
            Table(2, headers=['1'])
        with self.assertRaises(AssertionError):
            Table(2, headers=['1', '2', '3'])
        with self.assertRaises(AssertionError):
            Table(2, coltypes=['str'])
        with self.assertRaises(AssertionError):
            Table(2, headers=['str', 'str', 'str'])

    def test_too_many_cols(self):
        t = Table(2)
        with self.assertRaises(AssertionError):
            t.add_row(['1', '2', '3'])
        with self.assertRaises(AssertionError):
            t.set_rows([['a', 'b'], ['1', '2', '3']])

    def test_too_few_cols(self):
        t = Table(2)
        t.add_row(['1'])
        t.set_rows([['1', '2'], ['1'], ['a']])


if __name__ == '__main__':
    unittest.main()
