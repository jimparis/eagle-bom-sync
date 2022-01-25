import typing
import lxml.etree # type: ignore

from .bom import *

class EagleError(Exception):
    pass

class EagleReader:
    sch: str
    brd: str

    def __init__(self, sch: str, brd: str) -> None:
        self.sch = sch
        self.brd = brd

    def __call__(self) -> typing.Generator[Part, None, None]:

        # Read the SCH and BRD files
        with open(self.sch) as f:
            sch = lxml.etree.parse(f)
        with open(self.brd) as f:
            brd = lxml.etree.parse(f)

        missing_bom = []

        # Grab each part.  We use parts from the board, so that we
        # don't get schematic-only symbols (like GND).
        for part in brd.findall('/drawing/board/elements/element'):
            desig = part.get('name')
            eagle_value = part.get('value', '')
            eagle_package = part.get('package', '')

            if '$' in desig:
                continue

            # Grab all key/value attributes
            data = {}
            for attr in part.findall('attribute'):
                name = attr.get('name')
                value = attr.get('value')
                data[name] = value

            # Find all variants
            variants: dict[int, bool] = {}
            for key in data:
                m = re.match(r'^BOM_VAR_([0-9]+)_', key)
                if m:
                    variants[int(m.group(1))] = True

            if not len(variants):
                missing_bom.append(desig)
                variants[0] = True

            # For each variant, yield the data
            for v in sorted(variants):

                def get(name, defval=''):
                    return data.get(f'BOM_VAR_{v}_{name}', defval)

                info = Info(package=get('PACKAGE'),
                            description=get('DESCRIPTION'),
                            manufacturer=get('MANUFACTURER'),
                            part=get('PART'),
                            supplier=get('SUPPLIER'),
                            supplier_part=get('SUPPLIER_PART'),
                            notes=get('NOTES'),
                            alternatives=get('ALTERNATIVES'),
                            status=get('STATUS'),
                            eagle_value=eagle_value,
                            eagle_package=eagle_package,
                            )
                if get('DNP', False) == "1":
                    info.dnp = True

                rules = get('VARIANT_RULES')

                yield Part(desig=desig, variants=[ (rules, info) ])

        if missing_bom:
            log(f"----");
            log(f"---- Missing BOM data for: {' '.join(missing_bom)}");
            log(f"----");


class EagleWriter:
    sch: str
    brd: str

    def __init__(self, sch: str, brd: str) -> None:
        self.sch = sch
        self.brd = brd

    def __call__(self, parts: dict[str, Part],
                 variants: Optional[list[str]]) -> None:

        # Read the SCH and BRD files
        with open(self.sch) as f:
            sch = lxml.etree.parse(f)
        with open(self.brd) as f:
            brd = lxml.etree.parse(f)

        # Remove any of our Eagle attributes that already exist in the files
        for elem in (sch.findall('/drawing/schematic/parts/part/attribute') +
                     brd.findall('/drawing/board/elements/element/attribute')):
            name = elem.get('name')
            if (name.startswith('BOM_')
                or name in ( 'DNP',
                             'MANUFACTURER',
                             'MPN',
                             'PARTNUMBER',
                             'POPULATE' )):
                elem.getparent().remove(elem)

        def set_attribute(elem, name, value):
            att = lxml.etree.SubElement(elem, "attribute")
            # Copy "tail" of element to the new attribute, to match
            # Eagle output formatting
            att.tail = elem.tail
            att.set("name", name)
            att.set("value", value)
            if elem.get("x") is not None:
                # Board attributes need position/display data
                att.set("x", elem.get("x"))
                att.set("y", elem.get("y"))
                att.set("size", "1")
                att.set("layer", "27")
                att.set("rot", "R180")
                att.set("display", "off")

        # For every part, populate attributes in both
        for part in parts.values():
            sch_elem = sch.findall(
                f'/drawing/schematic/parts/part[@name="{part.desig}"]')
            if len(sch_elem) != 1:
                raise EagleError(f"Part {part.desig} not found in schematic")

            brd_elem = brd.findall(
                f'/drawing/board/elements/element[@name="{part.desig}"]')
            if len(brd_elem) != 1:
                raise EagleError(f"Part {part.desig} not found in board")

            # Populate attributes in schematic and board
            for elem in (sch_elem[0], brd_elem[0]):

                # For each variant row n, create BOM_VAR_n_... attributes
                for (n, (rules, info)) in enumerate(part.variants):

                    def add(name, value):
                        set_attribute(elem, f"BOM_VAR_{n}_{name}", value)

                    # Only add variant rules to Eagle if we haven't selected
                    # a variant.
                    if not variants:
                        add("VARIANT_RULES", rules)
                    add("PACKAGE", info.package)
                    add("DESCRIPTION", info.description)
                    add("MANUFACTURER", info.manufacturer)
                    add("PART", info.part)
                    add("SUPPLIER", info.supplier)
                    add("SUPPLIER_PART", info.supplier_part)
                    add("NOTES", info.notes)
                    add("ALTERNATIVES", info.alternatives)
                    add("STATUS", info.status)
                    add("DNP", "1" if info.dnp else "0")

                # If we did not select a variant, skip the attributes for
                # assembly.
                if not variants:
                    continue

                if len(part.variants) != 1:
                    raise EagleError(f"A variant was selected, but " +
                                     f"{part.desig} still has more than " +
                                     f"one option")

                (rules, info) = part.variants[0]
                set_attribute(elem, "BOM_VARIANTS", " ".join(variants))
                set_attribute(elem, "DNP", "1" if info.dnp else "0")
                set_attribute(elem, "MANUFACTURER", info.manufacturer)
                maybe_part = "NOT_POPULATED" if info.dnp else info.part
                set_attribute(elem, "MPN", maybe_part)
                set_attribute(elem, "PARTNUMBER", maybe_part)
                set_attribute(elem, "POPULATE", "0" if info.dnp else "1")

        # Write the SCH and BRD files
        for (tree, outfile) in [ (sch, self.sch), (brd, self.brd) ]:
            with open(outfile, "w") as f:
                f.seek(0)
                f.write(lxml.etree.tostring(tree).decode("utf-8"))
                f.write('\n')
                f.truncate()
