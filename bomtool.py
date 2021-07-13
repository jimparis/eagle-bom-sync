#!/usr/bin/python3

import bomtool

def main(argv):
    import argparse
    parser = argparse.ArgumentParser(
        prog=argv[0],
        description="Synchronize BOM between files and manage variants")

    group = parser.add_argument_group('Input Options')
    ex = group.add_mutually_exclusive_group(required=True)
    ex.add_argument("-i", "--in", metavar="FILE",
                    help="Input from spreadsheet, based on extension " +
                    "(csv, ods, xlsx)")
    ex.add_argument("-I", "--in-eagle", metavar=("SCH", "BRD"), nargs=2,
                    help="Extract attributes from Eagle files")

    group = parser.add_argument_group('Output Options')
    ex = group.add_mutually_exclusive_group(required=True)
    ex.add_argument("-o", "--out", metavar="FILE",
                    help="Output to spreadsheet, based on extension " +
                    "(csv, ods, xlsx)")
    ex.add_argument("-O", "--out-eagle", metavar=("SCH", "BRD"), nargs=2,
                    help="Inject attributes into Eagle files")

    group.add_argument("-e", "--eagle-value", action="store_true",
                       help="With Eagle input, include Eagle value in output")
    group.add_argument("-s", "--separate", action="store_true",
                       help="In spreadsheets, output one designator per row")

    group = parser.add_argument_group('Variant Filtering')
    group.add_argument("-v", "--variant", metavar="VAR1[,VAR2]...",
                       help="Variant rule flags, comma-separated")

    args = parser.parse_args(argv[1:])
    run(vars(args))

def run(args):
    bom = bomtool.BOM()

    # Read input
    if args['in']:
        reader = bomtool.SheetReader(args['in'])
    else:
        (sch, brd) = args['in_eagle']
        reader = bomtool.EagleReader(sch, brd)
    bom.read(reader)

    if args['variant']:
        variants = args['variant'].split(',')
        print(f"Extracting BOM for variant: {' '.join(variants)}")
    else:
        variants = None
        print(f"Extracting master BOM for all variants")

    # Write output
    if args['out']:
        writer = bomtool.SheetWriter(args['out'],
                                     merge=not args['separate'],
                                     eagle_value=args['eagle_value'])
    else:
        (sch, brd) = args['out_eagle']
        writer = bomtool.EagleWriter(sch, brd)
    bom.write(writer, variants)

if __name__ == "__main__":
    import sys
    main(sys.argv)
