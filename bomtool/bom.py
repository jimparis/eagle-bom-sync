import re
import sys
import copy
import collections
import dataclasses

from typing import Optional, Generator

def log(fmt, *args):
    if isinstance(fmt, str):
        out = fmt % args
    else:
        out = ' '.join(map(str, [fmt, *args]))
    print(out, end='\n', file=sys.stderr)

Desig = str
VariantRules = str

@dataclasses.dataclass(unsafe_hash=True, order=True)
class Info:
    """BOM info for a single part designator in a single variant.

    This is the info that should go into final output files for sending
    to a manufacturer."""
    package: str
    description: str
    manufacturer: str
    part: str
    supplier: str
    supplier_part: str
    notes: str              # "Other notes" field in CSV
    alternatives: str
    status: str
    dnp: bool = False       # goes into "Notes" field in CSV
    eagle_value: str = ""   # Only filled when reading Eagle files
    eagle_package: str = "" # Only filled when reading Eagle files

Variants = list[tuple[VariantRules, Info]]

@dataclasses.dataclass
class Part:
    """Information about a specific part designator, which may have
    different versions controlled by variant rules.  If multiple versions
    are present, the variant rule should exclude all but one."""
    desig: Desig
    variants: Variants

class BOMReader:
    def __call__(self) -> Generator[Part, None, None]:
        """Yield each Part as it's read.  The same designator may be returned
        multiple times, and the variants will be merged."""
        raise NotImplementedError("subclass needs to define this")

class BOMWriter:
    def __call__(self, parts: dict[str, Part],
                 variants: Optional[list[str]]) -> None:
        """Write all of the parts."""
        raise NotImplementedError("subclass needs to define this")

class BOM:
    # Mapping between designator and a list of variants for this part
    parts: dict[Desig, Part]

    def __init__(self) -> None:
        self.parts = {}

    def append(self, part: Part) -> None:
        """Add a part to this BOM, appending to variants when needed"""
        if part.desig not in self.parts:
            self.parts[part.desig] = part
        else:
            self.parts[part.desig].variants.extend(part.variants)

    def read(self, reader: BOMReader) -> None:
        """Read BOM data using the specified reader"""
        for part in reader():
            self.append(part)

    def write(self, writer: BOMWriter,
              variants: Optional[list[str]] = None) -> None:
        """Filter BOM according to the given variants, and send to
        the specified writer."""

        if variants is None:
            # No variants specified, so write everything as-is
            out_bom = self

        else:
            # Process variant rules and filter things out
            out_bom = BOM()
            for (desig, part) in self.parts.items():
                for (rules, info) in copy.deepcopy(part.variants):
                    flags = parse_variant_rules(rules, variants)
                    # Variant rule can only _set_ DNP; it may already be
                    # true because of the Notes field in the file.
                    if flags["dnp"]:
                        info.dnp = True
                    if not flags["exclude"]:
                        out_bom.append(Part(desig, [(rules, info)]))

        writer(out_bom.parts, variants)

    # Print all parts
    def __str__(self) -> str:
        try:
            return f"BOM({' '.join(list(self.parts.keys()))})"
        except AttributeError:
            return "BOM(empty)"

class VariantRuleEngine(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flags = { "dnp": False, "exclude": False }

    def USER_dnp(self, val=True):
        """If parameter is True, mark this part DNP"""
        if val:
            self.flags["dnp"] = True

    def USER_only(self, val):
        """If parameter is not True, mark this part DNP"""
        if not val:
            self.flags["dnp"] = True

    def USER_exclude(self, val=True):
        """If parameter is not True, exclude from output"""
        if val:
            self.flags["exclude"] = True

    def __getitem__(self, key):
        if key.startswith("_"):
            raise KeyError()

        # Key in this class (function call)?
        try:
            val = getattr(self, "USER_" + key)
            return val
        except AttributeError:
            pass

        # Key in the original dictionary (variant flag)?
        if key in self:
            return super().__getitem__(key)

        # No key -- assume False
        return False

def parse_variant_rules(rules: VariantRules,
                        variants: list[str]) -> dict[str, bool]:
    """Parse variant rules, which are Python expressions that
    can contain function calls to set flags (based on variable
    names that match the currently set variants):

    dnp(foo) -> mark part as DNP if "foo" variant is set
    only(foo or bar) -> mark part as DNP unless "foo" or "bar" is set
    exclude(not foo) -> exclude from output if "foo" variant isn't set
    """

    engine = VariantRuleEngine()
    for var in variants:
        engine[var] = True

    # Individual rules can be separated by comma or semicolon
    for rule in re.split(' *[;,] *', rules):
        if rule == '':
            continue
        eval(rule, {}, engine)

    return engine.flags
