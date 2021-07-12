# eagle-bom-sync

This script synchronizes a PCB Bill of Materials between files, such as:
  - Eagle (BRD and SCH)
  - Spreadsheet (CSV, XLS, ODS)

The general workflow is to create an initial BOM manually in a
spreadsheet, that includes info for all assembly variants.  Then, this
data is injected into attributes within the Eagle design files.  This
is done for two reasons:

- Injecting the BOM info into the design files allows assembly houses
  like CircuitHub and Tempo to extract the correct info.

- You can manipulate things inside the PCB software (changing
  reference designators, copying components) and then re-extract an
  updated BOM.

# Variants

All variant info is stored together in the "primary" spreadsheet or
design files.  Simplified boards and BOM output can be generated for
any variant.

Variant rules are simple Python expressions that can contain function
calls to set flags, based on variable names are "True" if they appear
in the list of currently set variants.  Basic action functions are
available, for example:

    dnp(foo) -> mark part as DNP if "foo" variant is set
    only(foo or bar) -> mark part as DNP unless "foo" or "bar" is set
    exclude(not foo) -> exclude from output if "foo" variant isn't set
