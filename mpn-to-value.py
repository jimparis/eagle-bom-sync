#!/usr/bin/python

# Move manufacturer part number to the part values.  This is the easiest
# way to get CircuitHub to pull in the right stuff.

from __future__ import print_function
def printf(str, *args):
    print(str % args, end='')
def fprintf(file, str, *args):
    print(str % args, end='', file=file)

import csv
import sys
import lxml.etree

def get_att_value(part, name, default=""):
    att = part.find('attribute[@name="%s"]' % name)
    if att is None:
        return default
    return att.get("value")

def set_values(brdin, schin, brdout, schout):
    brd = lxml.etree.parse(brdin)
    sch = lxml.etree.parse(schin)

    mpns = {}
    for brdpart in brd.findall('/drawing/board/elements/element'):
        name = brdpart.get("name")

        mpn = get_att_value(brdpart, "BOM_PART", None)
        if mpn is None:
            if "$" not in name:
                printf("warning: no BOM_PART for board element %s\n", name)
            continue

        # Set value to to DO_NOT_POPULATE if "DNP" is in BOM_NOTES,
        # or if manufacturer part number is empty
        if mpn == "" or "DNP" in get_att_value(brdpart, "BOM_NOTES"):
            mpn = "DO_NOT_POPULATE"

        brdpart.set("value", mpn)
        mpns[name] = mpn

    for schpart in sch.findall('/drawing/schematic/parts/part'):
        name = schpart.get("name")
        if name not in mpns:
            continue
        schpart.set("value", mpns[name])

    brd.write(brdout)
    sch.write(schout)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Move manufacturer PN into part values, for CircuitHub")
    parser.add_argument("-i", "--input", required=True,
                        metavar=("IN.BRD","IN.SCH"),
                        nargs=2, type=argparse.FileType("r"),
                        help="Input")
    parser.add_argument("-o", "--output", required=True,
                        metavar=("OUT.BRD","OUT.SCH"),
                        nargs=2, type=argparse.FileType("w"),
                        help="Output")
    args = parser.parse_args()
    set_values(args.input[0], args.input[1], args.output[0], args.output[1])

