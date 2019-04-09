# eagle-bom-sync

This script synchronizes a PCB Bill of Materials between a CSV file
and an Eagle design (BRD and SCH).  The general workflow is to create
an initial BOM manually in a CSV, then inject attributes into the
Eagle files corresponding to those BOM entries.  This is done for two
reasons:

- Injecting the BOM info into the Eagle files allows Assembly houses
  like CircuitHub and Tempo can extract the correct info.

- You can manipulate things inside Eagle (changing reference
  designators, copying components) and then re-extract an updated BOM
  CSV.
