import os
import csv
import tempfile
import functools
import subprocess
import xlsxwriter # type: ignore

from .csv import *
from typing import Any

class SheetReader(CSVReader):
    """Use ssconvert from Gnumeric to convert the input file to csv, then
    read it with CSVReader

    """
    def __call__(self) -> typing.Generator[Part, None, None]:
        # If CSV, input it directly
        if self.path.endswith('.csv'):
            yield from super().__call__()
            return

        with tempfile.TemporaryDirectory() as tempdir:
            temp_csv = os.path.join(tempdir, "converted.csv")
            print(f"Converting from {self.path}")
            subprocess.run(["ssconvert", self.path, temp_csv], check=True)
            yield from CSVReader(temp_csv)()

class SheetWriter(CSVWriter):
    """Write a temporary XLSX file to get formatting correct, then use
    ssconvert from Gnumeric to convert to the output file

    """
    def __call__(self, parts: dict[str, Part],
                 variants: Optional[list[str]]) -> None:
        # If CSV, output it directly
        if self.path.endswith('.csv'):
            return super().__call__(parts, variants)

        # Otherwise, do the full write/read/write/convert
        with tempfile.TemporaryDirectory() as tempdir:
            self.call_with_tempdir(tempdir, parts, variants)

    def call_with_tempdir(self, tempdir: str,
                          parts: dict[str, Part],
                          variants: Optional[list[str]]) -> None:

        # First write to CSV
        temp_csv = os.path.join(tempdir, "out.csv")
        writer = CSVWriter(path=temp_csv,
                           merge=self.merge,
                           eagle_value=self.eagle_value)
        writer(parts, variants)

        # Now re-read the CSV
        data = []
        with open(temp_csv, "r") as f:
            reader = csv.DictReader(f, restval='')
            header = list(reader.fieldnames or [])
            data.append(header)
            for csv_row in reader:
                csv_row['Qty'] = int(csv_row['Qty'])
                data.append(list(csv_row.values()))

        # Create XLSX

        sheet_name = 'BOM'
        if variants:
            sheet_name += f' ({",".join(variants)})'

        temp_xlsx = os.path.join(tempdir, "out.xlsx")
        workbook = xlsxwriter.Workbook(temp_xlsx)
        worksheet = workbook.add_worksheet(sheet_name)

        # Build default format for every cell
        base_format = {
            "font": "Arial",
            "font_size": 10,
            "border": 1,
            "border_color": '#cccccc',
        }
        formats: list[list[dict[str, Any]]] = []
        for datarow in data:
            formats.append([ base_format ] * len(datarow))

        # Add formats to a cell, row, or column
        def format_cell(row: int, col: int, fmt: dict[str, Any]) -> None:
            formats[row][col] = dict(formats[row][col], **fmt)

        def format_row(row: int, fmt: dict[str, Any]) -> None:
            for col in range(len(formats[row])):
                format_cell(row, col, fmt)

        def format_col(col: int, fmt: dict[str, Any]) -> None:
            for row in range(len(formats)):
                format_cell(row, col, fmt)

        # Get column number with given name
        @functools.cache
        def field(name: str) -> int:
            return header.index(name)

        # Format header
        format_row(0, { 'bg_color': '#ccddff', 'bold': True, 'bottom': 1 })

        # DNP rows are styled differently
        for row in range(len(data)):
            if data[row][field('Notes')] == 'DNP':
                format_row(row, { 'bg_color': '#cccccc', 'italic': True })
                format_cell(row, field('Designators'),
                            { 'font_strikeout': True })

        # Column sizes
        desig_width = 28

        def set_width(name: str, width: float, wrap: bool = False) -> None:
            worksheet.set_column(field(name), field(name), width)
            if wrap:
                format_col(field(name), { 'text_wrap': True })
        set_width('Notes', 7)
        set_width('Qty', 3)
        set_width('Package', 11)
        set_width('Description', 32)
        set_width('Manufacturer', 20)
        set_width('Part', 28)
        set_width('Designators', desig_width, True)
        set_width('Supplier', 13)
        set_width('Supplier part', 35)
        set_width('Variant rule', 20)
        set_width('Other notes', 48, True)
        set_width('Alternatives', 48, True)
        set_width('Status', 48, True)

        if 0:
            # Set row height to account for wraps in Designators.
            # Most spreadsheets do this automatically on open, but
            # Gnumeric does not.  But, setting explicit height disables
            # any automatic sizing, which I'd prefer to keep for now.
            for row in range(len(data)):
                n = len(data[row][field('Designators')]) // (desig_width - 2)
                worksheet.set_row(row, 18 * (n + 1))
                format_row(row, { 'valign': 'top' } )

        # Write cell contents and formats
        memoized_formats = {}
        for row in range(len(data)):
            for col in range(len(data[row])):
                fmt = formats[row][col]
                key = frozenset(fmt)
                if key not in memoized_formats:
                    memoized_formats[key] = workbook.add_format(fmt)
                worksheet.write(row, col, data[row][col], memoized_formats[key])

        # Freeze header
        worksheet.freeze_panes(1, 0)

        workbook.close()

        # Now convert to whatever we asked for
        subprocess.run(["ssconvert", temp_xlsx, self.path], check=True)
        print(f"Converted to {self.path}")
