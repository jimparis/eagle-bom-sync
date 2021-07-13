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
        reader_class = bomtool.SheetReader
        if args['in'].endswith('.csv'):
            reader_class = bomtool.CSVReader
        with reader_class(args['in']) as reader:
            bom.read(reader)
    else:
        (sch, brd) = args['in_eagle']
        with bomtool.EagleReader(sch, brd) as reader:
            bom.read(reader)

    # Write output
    if args['out']:
        writer_class = bomtool.
        pass

    raise
    if args.inject:
        bom_to_attributes(args.inject[0], args.inject[1], args.inject[2])
    else:
        if not args.variant:
            variants = None
            log(f"Extracting master BOM for all variants")
        else:
            variants = args.variant.split(',')
            log(f"Extracting BOM specific to variants: {variants}")
        attributes_to_bom(args.extract[0], args.extract[1],
                          args.value, args.separate, variants)

if __name__ == "__main__":
    import sys
    main(sys.argv)
