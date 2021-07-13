import re
import csv
import typing
import natsort # type: ignore
import collections

from .bom import *

class DataError(Exception):
    def __init__(self, data, message=""):
        super(DataError, self).__init__(
            message + ": " + repr(data))

class CSVReader(BOMReader):
    path: str

    def __init__(self, path: str) -> None:
        self.path = path

    def __call__(self) -> typing.Generator[Part, None, None]:
        with open(self.path, "r") as f:
            reader = csv.DictReader(f, restval='')

            # For each row in the CSV, extract designators and add to BOM
            for row in reader:

                def field(name: str) -> str:
                    if name not in row:
                        raise DataError(reader.fieldnames,
                                        f"Expected field {name} not in CSV")
                    return row[name]

                if not any(row[k] != "" for k in row):
                    continue

                # Designators are separated by whitespace, commas, etc
                desig = re.split(' *[;, ] *', field('Designators'))

                def warn(msg: str):
                    print(f'Warning: {msg} for designators ' + ' '.join(desig))

                info = Info(package=field('Package'),
                            description=field('Description'),
                            manufacturer=field('Manufacturer'),
                            part=field('Part'),
                            supplier=field('Supplier'),
                            supplier_part=field('Supplier part'),
                            notes=field('Other notes'))

                # Notes field should just contain DNP or be empty
                notes = field('Notes')
                if notes == 'DNP':
                    info.dnp = True
                elif notes != '':
                    warn(f'ignoring unknown notes "{notes}"')

                # If DNP, quantity should be zero, otherwise, it should match
                if info.dnp and int(field('Qty')) != 0:
                    warn(f"quantity should be zero for DNP parts")
                if not info.dnp and int(field('Qty')) != len(desig):
                    warn(f"wrong quantity {field('Qty')}")

                # Ensure we can parse the variant rules
                rules = field('Variant rule')
                try:
                    parse_variant_rules(rules, [])
                except (SyntaxError, TypeError) as e:
                    warn(f"can't parse variant rule \"{rules}\" ({str(e)})")

                # Add to BOM
                for d in desig:
                    yield Part(desig=d, variants=[ (rules, info) ])

class CSVWriter(BOMWriter):
    path: str
    printed_header: bool
    csv: typing.IO
    merge: bool
    eagle_value: bool

    def __init__(self, path: str,
                 merge: bool=True,
                 eagle_value: bool=False) -> None:
        self.path = path
        self.merge = merge
        self.eagle_value = eagle_value

    def write_csv_line(self, keyval: collections.OrderedDict[str, str]):
        row = []
        if not self.printed_header:
            self.printed_header = True
            header = collections.OrderedDict([ (k, k) for k in keyval ])
            self.write_csv_line(header)

        for (k, v) in keyval.items():
            if '"' in v:
                raise Exception(f"Can't handle double quotes in CSV file: {v}")
            if ',' in v or ' ' in v:
                v = '"' + v + '"'
            row.append(v)
        self.csv.write(','.join(row) + '\n')

    def __call__(self, parts: dict[str, Part],
                 variants: Optional[list[str]]) -> None:

        # Gather parts by designator
        out_parts: dict[str, Part] = {}

        hide_variant_rules = variants is not None

        if self.merge:
            # Merge designators where all other fields match
            memo = collections.defaultdict(list)
            for part in parts.values():
                if hide_variant_rules:
                    # Exclude variant rules from the key that we use to merge,
                    # since we won't include that column in the output
                    v = [ ('', i) for (r, i) in part.variants ]
                else:
                    v = part.variants
                key = tuple(sorted(v))
                memo[key].append(part.desig)
            for key in memo:
                desig = ' '.join(natsort.natsorted(memo[key]))
                out_parts[desig] = Part(desig, list(key))
        else:
            # Keep all parts separate
            for part in parts.values():
                out_parts[part.desig] = part

        # Print all rows
        self.printed_header = False
        with open(self.path, "w") as self.csv:
            for desig in natsort.natsorted(out_parts):
                for (rules, info) in out_parts[desig].variants:
                    if info.dnp:
                        notes = "DNP"
                        qty = 0
                    else:
                        notes = ""
                        qty = len(desig.split())

                    row = collections.OrderedDict()
                    row['Notes'] = notes
                    row['Qty'] = str(qty)
                    row['Package'] = info.package
                    row['Description'] = info.description
                    row['Manufacturer'] = info.manufacturer
                    row['Part'] = info.part
                    row['Designators'] = desig
                    row['Supplier'] = info.supplier
                    row['Supplier part'] = info.supplier_part
                    if not hide_variant_rules or True:
                        row['Variant rule'] = rules
                    row['Other notes'] = info.notes
                    self.write_csv_line(row)

        if variants is None:
            print(f"Wrote {self.path} as master BOM for all variants")
        elif len(variants) == 0:
            print(f"Wrote {self.path} for base variant")
        else:
            print(f"Wrote {self.path} for variants: {' '.join(variants)}")


