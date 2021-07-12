import os
import csv
import tempfile
import functools
import subprocess
import xlsxwriter # type: ignore

from .csv import *
from typing import Any

class SheetReader(BOMReader):
    """Use ssconvert from Gnumeric to convert the input file to csv, then
    read it with CSVReader

    """
    path: str

    def __init__(self, path: str) -> None:
        self.path = path

    def __enter__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        return self

    def __exit__(self, *args):
        self.tempdir.cleanup()

    def __call__(self) -> typing.Generator[Part, None, None]:
        temp_csv = os.path.join(self.tempdir.name, "converted.csv")
        print(f"Converting from {self.path}")
        subprocess.run(["ssconvert", self.path, temp_csv], check=True)
        with CSVReader(temp_csv) as reader:
            yield from reader()

class SheetWriter(BOMWriter):
    """Write a temporary XLSX file to get formatting correct, then use
    ssconvert from Gnumeric to convert to the output file

    """
    path: str

    def __init__(self, path: str, merge: bool=True) -> None:
        self.path = path
        self.merge = merge

    def __enter__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        return self

    def __exit__(self, *args):
        self.tempdir.cleanup()

    def __call__(self, parts: dict[str, Part],
                 variants: Optional[list[str]]) -> None:

        # First write to CSV
        temp_csv = os.path.join(self.tempdir.name, "out.csv")
        with CSVWriter(path=temp_csv, merge=self.merge) as writer:
            writer(parts, variants)

        # Now re-read the CSV
        data = []
        with open(temp_csv, "r") as f:
            reader = csv.DictReader(f, restval='')
            header = list(reader.fieldnames or [])
            data.append(header)
            for csv_row in reader:
                data.append(list(csv_row.values()))

        # Create XLSX

        sheet_name = 'BOM'
        if variants:
            sheet_name += f' ({",".join(variants)})'

        temp_xlsx = os.path.join(self.tempdir.name, "out.xlsx")
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

        def set_width(name: str, width: float) -> None:
            worksheet.set_column(field(name), field(name), width)
        set_width('Notes', 7)
        set_width('Qty', 3)
        set_width('Package', 11)
        set_width('Description', 32)
        set_width('Manufacturer', 20)
        set_width('Part', 28)
        set_width('Designators', desig_width)
        set_width('Supplier', 13)
        set_width('Supplier part', 35)
        set_width('Variant rule', 20)
        set_width('Other notes', 48)

        # Designator column wraps.  Set height to account for wraps.
        format_col(field('Designators'), { 'text_wrap': True })
        for row in range(len(data)):
            wraps = len(data[row][field('Designators')]) // (desig_width - 2)
            worksheet.set_row(row, 18 * (wraps + 1))
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

        workbook.close()

        # Now convert to whatever we asked for
        subprocess.run(["ssconvert", temp_xlsx, self.path], check=True)
        print(f"Converted to {self.path}")
