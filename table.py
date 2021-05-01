"""Module to help output and print tables."""

from tabulate import tabulate

class Table():
  def __init__(self, numcols, headers=(), coltypes=None):
    assert numcols > 0
    self._numcols = numcols

    if headers:
      assert len(headers) == numcols
    self._headers = headers

    coltype2func = {
      None: lambda x: x,
      'str': lambda x: str(x),
      'dollars': lambda x: '${:,.2f}'.format(x),
      'delta_dollars': lambda x: '{}${:,.2f}'.format(
        '-' if x < 0 else '+', abs(x)),
      'percentage': lambda x: '{}%'.format(round(100*x)),
    }

    if coltypes:
      assert len(coltypes) == numcols
      self._colfunc = []
      self._colalign = []
      for coltype in coltypes:
        self._colfunc.append(coltype2func[coltype])
        self._colalign.append(
          'right' if coltype == 'dollars' or coltype == 'delta_dollars'
          else 'left')
    else:
      self._colfunc = [coltype2func[None]] * numcols
      self._colalign = ['left'] * numcols

    self._rows = []

  def AddRow(self, row):
    self._rows.append(row)

  def SetRows(self, rows):
    self._rows = rows

  def Headers(self):
    return self._headers

  def ColAlign(self):
    return self._colalign

  def List(self):
    return self._rows

  def StrList(self):
    ret_list = []
    for row in self.List():
      ret_row = []
      for col_num in range(len(row)):
        ret_row.append(self._colfunc[col_num](row[col_num]))
      ret_list.append(ret_row)
    return ret_list

  def String(self, tablefmt='simple'):
    str_list = self.StrList()
    if not str_list:
      return ''

    return tabulate(str_list,
                    headers = self.Headers(),
                    tablefmt = tablefmt,
                    colalign = self.ColAlign())
