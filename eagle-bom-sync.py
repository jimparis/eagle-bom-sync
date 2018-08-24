#!/usr/bin/python

# Synchronize between a bill-of-materials in CSV format, and
# attributes that represent that same BOM data in an Eagle SCH file.

from __future__ import print_function
def printf(str, *args):
    print(str % args, end='')
def fprintf(file, str, *args):
    print(str % args, end='', file=file)

import fileinput
import csv
import sys
import natsort
import io
import re
import lxml.etree
import collections

class DataError(Exception):
    def __init__(self, data, message=""):
        super(DataError, self).__init__(
            message + ": " + repr(data))

def update_part_attribute(part, name, value):
    """Update attribute for a given part"""
    att = part.find('attribute[@name="%s"]' % name)
    if att is None:
        att = lxml.etree.SubElement(part, "attribute")
    att.set("name", name)
    att.set("value", value)
    if part.get("x") is not None:
        # Board attributes need position/display data
        att.set("x", part.get("x"))
        att.set("y", part.get("y"))
        att.set("size", "1")
        att.set("layer", "27")
        att.set("rot", "R180")
        att.set("display", "off")

def update_tree(trees, desig, fields, row):
    """Update XML tree for item 'desig' with fields from 'row'"""
    elems = [
        trees[0].findall('/drawing/schematic/parts/part[@name="%s"]' % desig),
        trees[1].findall('/drawing/board/elements/element[@name="%s"]' % desig),
    ]
    if len(elems[0]) != 1:
        raise ValueError("Part %s not found in schematic" % desig)
    if len(elems[1]) != 1:
        raise ValueError("Part %s not found in board" % desig)
    for elem in elems:
        part = elem[0]
        for field in fields:
            if len(field) == 0:
                raise Exception("unexpected empty field??")
            # e.g. "Other notes" -> "BOM_OTHER_NOTES"
            att_name = "BOM_" + field.replace(' ','_').upper()
            update_part_attribute(part, att_name, row[field])

def get_att_value(part, name, default=""):
    att = part.find('attribute[@name="%s"]' % name)
    if att is None:
        return default
    return att.get("value")

def update_macrofab(trees):
    """Update XML tree with macrofab-specific attributes, based on the
    other attributes"""

    for part in (trees[0].findall('/drawing/schematic/parts/part') +
                 trees[1].findall('/drawing/board/elements/element')):
        # Is part populated?  Must have a non-empty "Part" column and
        # not be marked DNP in "Notes".
        populate = True
        if (get_att_value(part, "BOM_PART") == "" or
            "DNP" in get_att_value(part, "BOM_NOTES")):
            populate = False

        # Set POPULATE and DNP flag
        update_part_attribute(part, "POPULATE", "1" if populate else "0")
        update_part_attribute(part, "DNP", "0" if populate else "1")

        def set_mpn(field, supplier):
            # Set MPN to match BOM_PART, unless this is the attribute for
            # the supplier we're using, in which case use BOM_SUPPLIER_PART.
            mpn = ""
            if get_att_value(part, "SUPPLIER").lower() == supplier:
                mpn = get_att_value(part, "BOM_SUPPLIER_PART")
            if mpn == "":
                mpn = get_att_value(part, "BOM_PART")
            update_part_attribute(part, field, mpn)

        # Set MPN for MacroFab, and PartNumber for CircuitHub
        set_mpn("MPN", "macrofab")
        set_mpn("PARTNUMBER", "circuithub")

        # Set manufacturer
        update_part_attribute(part, "MANUFACTURER",
                              get_att_value(part, "BOM_MANUFACTURER"))

# BOM fields that must be present.  Some are treated specially.
required_bom_fields = [
    "Notes",
    "Qty",
    "Package",
    "Description",
    "Manufacturer",
    "Part",
    "Designators",
    "Supplier",
    "Supplier part",
    "Other notes",
]

def bom_to_attributes(csvfile, schfile, brdfile):
    """Extract BOM items from CSV file and insert into SCH+BRD file"""
    reader = csv.DictReader(csvfile, restval='')

    # Verify that the CSV contains all expected fields
    for field in required_bom_fields:
        if field not in reader.fieldnames:
            raise DataError(reader.fieldnames, "Expected field " +
                            "%s not in CSV" % field)

    # All fields except "Qty" and "Designators" get pushed into the Eagle file
    inject_fields = []
    for field in reader.fieldnames:
        if field == "Qty" or field == "Designators":
            continue
        inject_fields.append(field)

    # Open the SCH and BRD files
    trees = [ lxml.etree.parse(x) for x in (schfile, brdfile) ]

    # For each row in the CSV, extract designators and
    # inject into tree.
    all_designators = []
    for row in reader:
        designators = re.split(' *[;, ] *', row['Designators'])
        if not any(row[k] != "" for k in row):
            continue
        if row['Notes'] != 'DNP':
            if row['Qty'] == "":
                fprintf(sys.stderr, "Warning: missing quantity (%d) for: %s\n",
                        len(designators), designators)
            else:
                if len(designators) != int(row['Qty']):
                    raise DataError(row, "Part count doesn't match quantity")
        for desig in designators:
            if desig in all_designators:
                raise DataError(row, "Duplicate designator %s" % desig)
            all_designators.append(desig)
            update_tree(trees, desig, inject_fields, row)

    # Macrofab and Circuithub-specific attributes
    update_macrofab(trees)

    # Write the SCH and BRD files
    for (tree, outfile) in zip(trees, (schfile, brdfile)):
        outfile.seek(0)
        tree.write(outfile)
        outfile.truncate()

def csv_write_line(fields, keyval):
    if keyval is None:
        keyval = { x: x for x in fields }
    row = []
    for f in fields:
        v = str(keyval[f])
        if '"' in v:
            raise Exception("Can't handle double quotes in CSV file: " + keyval)
        if ',' in v or ' ' in v:
            v = '"' + v + '"'
        row.append(v)
    printf("%s\n", ','.join(row))

def attributes_to_bom(schfile, brdfile, include_value, separate):
    """Extract BOM items from SCH file and write CSV to stdout"""

    # Open the SCH and BRD files, although we really only need
    # one of them.
    trees = [ lxml.etree.parse(x) for x in (schfile, brdfile) ]

    csv_fields = required_bom_fields
    if include_value:
        csv_fields.insert(csv_fields.index("Other notes") + 1, "Eagle value")

    # Grab each part and group by designator.  We use parts from the
    # board, so that we don't get schematic-only symbols (like GND).
    parts = trees[1].findall('/drawing/board/elements/element')
    parts = natsort.natsorted(parts, key=lambda x: x.get("name"))

    lineitem = collections.defaultdict(list)
    unused = []

    for part in parts:
        desig = part.get("name")
        entries = {}
        for attr in part.findall('attribute'):
            name = attr.get("name")
            if name.startswith("BOM_") and len(name) > 4:
                field = name[4:].replace('_',' ').lower().capitalize()
                if field not in csv_fields:
                    csv_fields.append(field)
                value = attr.get("value")
                entries[field] = value

        # If we're including the Eagle values, we may be creating this
        # for the first time, so warn about (but ignore) missing fields
        missing_fields = []
        if include_value:
            entries["Eagle value"] = part.get("value")
            for field in required_bom_fields:
                # These don't get pushed into the Eagle file and aren't needed
                if field == "Qty" or field == "Designators":
                    continue
                if field not in entries:
                    missing_fields.append(field)
                    entries[field] = ""
        if len(missing_fields):
            fprintf(sys.stderr, "Warning: missing fields for %s: %s\n",
                    desig, ", ".join(missing_fields))

        if len(entries):
            lineitem[frozenset(entries.items())].append(desig)
        else:
            if "$" not in desig:
                unused.append(desig)

    # Start CSV file
    csv_write_line(csv_fields, None)

    # Sort designators
    for li in lineitem:
        lineitem[li] = natsort.natsorted(lineitem[li])

    # Now sort lineitems _by_ designators
    for li in natsort.natsorted(lineitem, key=lineitem.get):
        def write_line(data, designators):
            row = dict(data)
            row["Designators"] = " ".join(designators)
            row["Qty"] = len(designators)
            #if "Notes" in row and row["Notes"] == "DNP":
            #    row["Qty"] = 0
            csv_write_line(csv_fields, row)
        if separate:
            for x in lineitem[li]:
                write_line(li, [x])
        else:
            write_line(li, lineitem[li])

    if len(unused):
        fprintf(sys.stderr, "Warning: no BOM data for designators:\n  %s\n",
                " ".join(natsort.natsorted(unused)))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Synchronize BOM between a CSV and Eagle files")
    parser.add_argument("-v", "--value", action="store_true",
                        help="Include Eagle value column when extracting")
    parser.add_argument("-s", "--separate", action="store_true",
                        help="Separate line for each entry when extracting")
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument("-i", "--inject", metavar=("CSV", "SCH", "BRD"), nargs=3,
                       type=argparse.FileType("r+"),
                       help="Inject from CSV into SCH+BRD")
    group.add_argument("-e", "--extract", metavar=("SCH", "BRD"), nargs=2,
                       type=argparse.FileType("r"),
                       help="Extract from SCH+BRD (to stdout)")
    args = parser.parse_args()
    if args.inject:
        bom_to_attributes(args.inject[0], args.inject[1], args.inject[2])
    else:
        attributes_to_bom(args.extract[0], args.extract[1],
                          args.value, args.separate)

