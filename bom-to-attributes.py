#!/usr/bin/python

# Given a bill-of-materials in CSV format, inject attributes that
# represent the BOM data into an Eagle BRD file.

# Also puts them into a format suitable for Macrofab.

from __future__ import print_function
def printf(str, *args):
    print(str % args, end='')

import fileinput
import csv
import sys
import natsort
import io
import re
import lxml.etree

class DataError(Exception):
    def __init__(self, data, message=""):
        super(DataError, self).__init__(
            message + ": " + repr(data))

# Quote attribute names
#def att_name_dequote(s):
#    if not s.startswith('BOM_'):
#        return None
#    return s[4:].replace('_',' ').lower().capitalize()

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

def update_macrofab(tree):
    """Update XML tree with macrofab-specific attributes, based on the
    other attributes"""
    for part in tree.findall('/drawing/board/elements/element'):
        # Is part populated?
        populate = "1"
        att = part.find('attribute[@name="BOM_NOTES"]')
        if att is None or att.get("value") == "DNP":
            populate = "0"

        # Set POPULATE flag
        update_part_attribute(part, "POPULATE", populate)

        # Set MPN to match BOM_PART
        mpn = ""
        att = part.find('attribute[@name="BOM_PART"]')
        if att is not None:
            mpn = att.get("value")
        update_part_attribute(part, "MPN", mpn)

def bom_to_attributes(csvfile, brdfile):
    """Extract BOM items from CSV file and insert into BRD file"""
    reader = csv.DictReader(csvfile, restval='')

    csv_bom_fields = [
        "Notes",
        "Package",
        "Description",
        "Manufacturer",
        "Part",
        "Supplier",
        "Supplier part",
        "Other notes",
    ]
    csv_other_fields = [
        "Qty",
        "Designators",
    ]

    # Verify that the CSV contains all expected fields
    for field in (csv_bom_fields + csv_other_fields):
        if field not in reader.fieldnames:
            raise DataError(reader.fieldnames, "Expected field " +
                            "%s not in CSV" % field)

    # Open the BRD file
    tree = lxml.etree.parse(brdfile)

    # For each row in the CSV, extract designators and
    # inject into tree.
    for row in reader:
        designators = re.split(' *[;, ] *', row['Designators'])
        if row['Notes'] != 'DNP' and len(designators) != int(row['Qty']):
            raise DataError(row, "Designator count doesn't match quantity")
        for desig in designators:
            update_tree(tree, desig, csv_bom_fields, row)

    # Macrofab-specific attributes
    update_macrofab(tree)

    brdfile.seek(0)
    tree.write(brdfile)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Inject BOM from CSV into Eagle BRD file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('csv', metavar='csvfile', type=argparse.FileType('r'),
                        help='Input CSV')
    parser.add_argument('brd', metavar='brdfile', type=argparse.FileType('r+'),
                        help='Eagle BRD file to modify')
    args = parser.parse_args()
    bom_to_attributes(args.csv, args.brd)

