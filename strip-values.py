#!/usr/bin/python

# Strip value from all elements in schematic and board.
# This is for CircuitHub, which sometimes pays attention to value instead
# of the PARTNUMBER attribute.

from __future__ import print_function
def printf(str, *args):
    print(str % args, end='')
def fprintf(file, str, *args):
    print(str % args, end='', file=file)

import csv
import sys
import lxml.etree

def strip_values(brdin, schin, brdout, schout):
    tree = lxml.etree.parse(brdin)
    for part in tree.findall('/drawing/board/elements/element'):
        part.set("value", "")
    tree.write(brdout)

    tree = lxml.etree.parse(schin)
    for part in tree.findall('/drawing/schematic/parts/part'):
        part.set("value", "")
    tree.write(schout)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Strip values from SCH and BRD files")
    parser.add_argument("-i", "--input", required=True,
                        metavar=("IN.BRD","IN.SCH"),
                        nargs=2, type=argparse.FileType("r"),
                        help="Input")
    parser.add_argument("-o", "--output", required=True,
                        metavar=("OUT.BRD","OUT.SCH"),
                        nargs=2, type=argparse.FileType("w"),
                        help="Output")
    args = parser.parse_args()
    strip_values(args.input[0], args.input[1], args.output[0], args.output[1])

