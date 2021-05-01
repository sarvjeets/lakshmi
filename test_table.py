#!/usr/bin/python3

import table

import unittest

class TableTest(unittest.TestCase):
  def testEmptyTable(self):
    t = table.Table(3)
    self.assertListEqual([], t.List())
    self.assertListEqual([], t.StrList())
    self.assertEqual('', t.String())

  def testNoHeadersAndColTypes(self):
    t = table.Table(3)
    t.AddRow(['1', '2', '3'])
    self.assertListEqual([['1', '2', '3']],
                         t.List())
    self.assertListEqual([['1', '2', '3']],
                         t.StrList())
    self.assertGreater(len(t.String()), 0)

  def testSetRows(self):
    t = table.Table(3)
    t.SetRows([['1', '2']])
    self.assertListEqual([['1', '2']], t.StrList())

  def testHeadersAndDiffColTypes(self):
    headers = ['1', '2', '3', '4', '5']
    t = table.Table(
      5,
      headers = headers,
      coltypes = [None, 'str', 'dollars', 'delta_dollars', 'percentage'])

    rows = [['r1', 2, 3, 4.1, 0.5],
            ['r6', 7, 8, -9.2, 0.1]]
    t.SetRows(rows)

    self.assertListEqual(headers, t.Headers())
    self.assertListEqual(
      ['left', 'left', 'right', 'right', 'left'],
      t.ColAlign())

    self.assertListEqual(rows, t.List())
    self.assertListEqual(
      [['r1', '2', '$3.00', '+$4.10', '50%'],
       ['r6', '7', '$8.00', '-$9.20', '10%']],
      t.StrList())
    self.assertGreater(len(t.String()), 0)


if __name__ == '__main__':
  unittest.main()
