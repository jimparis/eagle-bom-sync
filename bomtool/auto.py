import os
import csv
import tempfile
import subprocess
import xlsxpandasformatter # type: ignore
import pandas # type: ignore
import pandas.io.formats.excel # type: ignore

from typing import Any
from .csv import *

class AutoReader(BOMReader):
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

class AutoWriter(BOMWriter):
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
        subprocess.run(f"cp -rv {self.tempdir.name} /tmp", shell=True)
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
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                data.append(list(row.values()))

        # Hack to prevent pandas from formatting header
        # https://stackoverflow.com/questions/36694313
        pandas.io.formats.excel.ExcelFormatter.header_style = None

        # Build XLSX using Pandas.  This is used (instead of
        # xlsxwriter) because we can use the XlsxPandasFormatter
        # module to help with output formatting.
        sheet_name = 'BOM'
        if variants:
            sheet_name += f' ({",".join(variants)})'

        df = pandas.DataFrame(data, columns=fieldnames)
        temp_xlsx = os.path.join(self.tempdir.name, "out.xlsx")
        writer = pandas.ExcelWriter(temp_xlsx, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        book = writer.book
        real_sheet = writer.sheets[sheet_name]

        # Wrap objects with xlsxpandasformatter to manage formatting
        sheet = xlsxpandasformatter.FormattedWorksheet(
            real_sheet, book, df, hasIndex=False)

        # Format it!
        sheet.freeze_header()

        default_font = 'DejaVu Sans'
        designator_width = 28

        # Header
        sheet.format_header(headerFormat=[{
            'bold': True, 'bg_color': '#ccddff', 'bottom': 1,
            'font': default_font, 'font_size': 10 }])

        # Rows
        for (n, thisrow) in enumerate(data):
            fmt = { 'font': default_font, 'font_size': 10 }
            if thisrow[fieldnames.index('Notes')] == 'DNP':
                fmt['bg_color'] = '#ffddaa'
                fmt['italic'] = True

            # Try to conservatively auto-size row height based on
            # designators wrapping
            height = ((len(thisrow[fieldnames.index('Designators')])
                       // (designator_width - 2)) + 1) * 15
            sheet.format_row(n, rowHeight=height, rowFormat=fmt)

        # Columns
        def col(name: str) -> int:
            return fieldnames.index(name)

        def set_width(name: str, width: float) -> None:
            sheet.worksheet.set_column(col(name), col(name), width)

        set_width('Notes', 7)
        set_width('Qty', 3)
        set_width('Package', 11)
        set_width('Description', 32)
        set_width('Manufacturer', 20)
        set_width('Part', 28)
        set_width('Designators', designator_width)
        set_width('Supplier', 13)
        set_width('Supplier part', 35)
        set_width('Variant rule', 20)
        set_width('Other notes', 48)

        sheet.format_col(col('Designators'), colFormat={ 'text_wrap': True })


        # Hack to prevent sheet.apply_format_table from crashing on index
        sheet.nIndexLevels = 0

        # Apply formats
        sheet.apply_format_table()

        # Save
        writer.save()


        # book = xlsxwriter.Workbook(temp_xlsx, { 'tmpdir': self.tempdir.name })
        # sheet = book.add_worksheet()

        # # Set default font/size
        # for fmt in book.formats:
        #     fmt.set_font('Sans')
        #     fmt.set_font_size(10)

        # format_props: dict[str, dict[str, Any]] = {
        #     'header':  { 'bg_color': '#ccddff', 'bold': True, 'bottom': 1 },
        #     'reg_row': { },
        #     'dnp_row': { 'bg_color': '#ffddaa', 'italic': True },
        #     'designators': { 'text_wrap': True },
        # }
        # formats = {}
        # for (k, v) in format_props.items():
        #     formats[k] = book.add_format(v)

        #     sheet.write_row(0, 0, header, formats['header'])
        #     for (n, data) in enumerate(reader):
        #         if data['Notes'] == 'DNP':
        #             fmt = formats['dnp_row']
        #         else:
        #             fmt = formats['reg_row']
        #         sheet.write_row(n + 1, 0, data.values(), fmt)

        #     sheet.write_column(0, header.index('Designators'),
        #                        [], formats['designators'])

        #     print(header.index('Designators'))

        # book.close()

        # Now convert to whatever we asked for
        subprocess.run(["ssconvert", temp_xlsx, self.path], check=True)
        print(f"Converted to {self.path}")
