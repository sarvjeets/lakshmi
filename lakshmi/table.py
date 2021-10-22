"""Module to help output and print tables."""

from tabulate import tabulate

import lakshmi.utils as utils


class Table():
    """This class helps format, process and print tabular information."""
    # Mapping from column type to a function that formats the cell
    # entries and converts them to a string.
    # Standard coltypes are:
    # 'str': Column is already in string format.
    # 'dollars': Column is a float which represents a dollar value.
    # 'delta_dollars': Column represents a positive or negative dollar
    # difference.
    # 'percentage': A float representing a percentage.
    # 'float': Float.
    coltype2func = {
        'str': lambda x: x,
        'dollars': lambda x: utils.format_money(x),
        'delta_dollars': lambda x: utils.format_money_delta(x),
        'percentage': lambda x: f'{round(100*x)}%',
        'float': lambda x: str(float(x)),
    }

    # Mapping of column type to how it should be aligned. Most values are
    # self explanatory. 'float' is aligned on the decimal point.
    coltype2align = {
        'str': 'left',
        'dollars': 'right',
        'delta_dollars': 'right',
        'percentage': 'right',
        'float': 'decimal',
    }

    def __init__(self, numcols, headers=(), coltypes=None):
        """
        Args:
            numcols: Number of columns (required)
            headers: Header row (optional)
            coltypes: The type of columns, if not provided the columns are
            assumed to be strings.
        """
        assert numcols >= 0
        self._numcols = numcols

        if headers:
            assert len(headers) == numcols
        self._headers = headers

        if coltypes:
            assert len(coltypes) == numcols
            assert set(coltypes).issubset(
                Table.coltype2func.keys()), 'Bad column type in coltypes'
            self._coltypes = coltypes
        else:
            self._coltypes = ['str'] * self._numcols

        self._rows = []

    def add_row(self, row):
        """Add a new row to the table.

        Args:
            row: A list of column entries representing a row.
        """
        assert len(row) <= self._numcols
        self._rows.append(row)
        return self

    def set_rows(self, rows):
        """Replaces all rows of this table by rows.

        Args:
            rows: A list (rows) of list (columns) of cell entries.
        """
        assert max(map(len, rows)) <= self._numcols
        self._rows = rows

    def headers(self):
        """Returns the header row."""
        return self._headers

    def col_align(self):
        """Returns the column alignment parameters.

        Returns: A list of strings, where each value represents
        the value of coltype2align map. These alignment parameters are
        dependent on the column types specified while constructing this
        object.
        """
        return list(map(lambda x: Table.coltype2align[x], self._coltypes))

    def list(self):
        """Returns the table as a list (row) of lists (raw columns).

        This function doesn't perform any string conversion on the cell values.
        """
        return self._rows

    def str_list(self):
        """Returns the table as a list (row) of list of strings (columns).

        This function converts the raw value of a cell to string based on its
        column type.
        """
        ret_list = []
        for row in self.list():
            ret_row = []
            for col_num in range(len(row)):
                if row[col_num] is None:
                    ret_row.append('')
                else:
                    ret_row.append(Table.coltype2func[self._coltypes[col_num]](
                        row[col_num]))
            ret_list.append(ret_row)
        return ret_list

    def string(self, tablefmt='simple'):
        """Returns the table as a formatted string."""
        str_list = self.str_list()
        if not str_list:
            return ''

        return tabulate(str_list,
                        headers=self.headers(),
                        tablefmt=tablefmt,
                        colalign=self.col_align())
