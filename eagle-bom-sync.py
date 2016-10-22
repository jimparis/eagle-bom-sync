#!/usr/bin/python

# Synchronize between a bill-of-materials in CSV format, and
# attributes that represent that same BOM data in an Eagle BRD file.

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
    att.set("x", part.get("x"))
    att.set("y", part.get("y"))
    att.set("size", "1")
    att.set("layer", "27")
    att.set("rot", "R180")
    att.set("display", "off")

def update_tree(tree, desig, fields, row):
    """Update XML tree for item 'desig' with fields from 'row'"""
    elem = tree.findall('/drawing/board/elements/element[@name="%s"]' % desig)
    if len(elem) != 1:
        raise ValueError("Part %s not found in board" % desig)
    part = elem[0]
    for field in fields:
        # e.g. "Other notes" -> "BOM_OTHER_NOTES"
        att_name = "BOM_" + field.replace(' ','_').upper()
        update_part_attribute(part, att_name, row[field])

def get_att_value(part, name, default=""):
    att = part.find('attribute[@name="%s"]' % name)
    if att is None:
        return default
    return att.get("value")

def update_macrofab(tree):
    """Update XML tree with macrofab-specific attributes, based on the
    other attributes"""

    for part in tree.findall('/drawing/board/elements/element'):
        # Is part populated?  Must have a non-empty "Part" column and
        # not be marked DNP in "Notes".
        populate = "1"
        if (get_att_value(part, "BOM_PART") == "" or
            "DNP" in get_att_value(part, "BOM_NOTES")):
            populate = "0"

        # Set POPULATE flag
        update_part_attribute(part, "POPULATE", populate)

        # Set MPN to match BOM_PART, or if the supplier is Macrofab,
        # use BOM_SUPPLIER_PART
        mpn = ""
        if get_att_value(part, "SUPPLIER").lower() == "macrofab":
            mpn = get_att_value(part, "BOM_SUPPLIER_PART")
        if mpn == "":
            mpn = get_att_value(part, "BOM_PART")
        update_part_attribute(part, "MPN", mpn)

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

def bom_to_attributes(csvfile, brdfile):
    """Extract BOM items from CSV file and insert into BRD file"""
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

    # Open the BRD file
    tree = lxml.etree.parse(brdfile)

    # For each row in the CSV, extract designators and
    # inject into tree.
    for row in reader:
        designators = re.split(' *[;, ] *', row['Designators'])
        if not any(row[k] != "" for k in row):
            continue
        if row['Notes'] != 'DNP' and len(designators) != int(row['Qty']):
            raise DataError(row, "Designator count doesn't match quantity")
        for desig in designators:
            update_tree(tree, desig, inject_fields, row)

    # Macrofab-specific attributes
    update_macrofab(tree)

    brdfile.seek(0)
    tree.write(brdfile)

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

def attributes_to_bom(brdfile, include_value):
    """Extract BOM items from BRD file and write CSV to stdout"""

    # Open the BRD file
    tree = lxml.etree.parse(brdfile)

    csv_fields = required_bom_fields
    if include_value:
        csv_fields.insert(csv_fields.index("Description"), "Eagle value")

    # Grab each part and group by designator
    lineitem = collections.defaultdict(list)
    unused = []
    for part in tree.findall('/drawing/board/elements/element'):
        desig = part.get("name")
        entries = {}
        for attr in part.findall('attribute'):
            name = attr.get("name")
            if name.startswith("BOM_"):
                field = name[4:].replace('_',' ').lower().capitalize()
                if field not in csv_fields:
                    csv_fields.append(field)
                value = attr.get("value")
                entries[field] = value
        if len(entries):
            if include_value:
                entries["Eagle value"] = part.get("value")
            lineitem[frozenset(entries.items())].append(desig)
        else:
            unused.append(desig)

    # Start CSV file
    csv_write_line(csv_fields, None)

    # Sort designators
    for li in lineitem:
        lineitem[li] = natsort.natsorted(lineitem[li])

    # Now sort lineitems _by_ designators
    for li in natsort.natsorted(lineitem, key=lineitem.get):
        row = dict(li)
        row["Designators"] = " ".join(lineitem[li])
        row["Qty"] = len(lineitem[li])
        if "Notes" in row and row["Notes"] == "DNP":
            row["Qty"] = 0
        # And write to CSV
        csv_write_line(csv_fields, row)

    if len(unused):
        fprintf(sys.stderr, "Warning: no BOM data for designators:\n  %s\n",
                " ".join(natsort.natsorted(unused)))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Synchronize BOM between a CSV and an Eagle BRD file")
    parser.add_argument("-v", "--value", action="store_true",
                        help="Include Eagle value column when extracting")
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument("-i", "--inject", metavar=("CSV", "BRD"), nargs=2,
                       type=argparse.FileType("r+"),
                       help="Inject from CSV into BRD")
    group.add_argument("-e", "--extract", metavar="BRD", nargs=1,
                       type=argparse.FileType("r"),
                       help="Extract from BRD (to stdout)")
    args = parser.parse_args()
    if args.inject:
        bom_to_attributes(args.inject[0], args.inject[1])
    else:
        attributes_to_bom(args.extract[0], args.value)

