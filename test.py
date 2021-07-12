#!/usr/bin/python3

import bomtool

bom = bomtool.BOM()
with bomtool.CSVReader("/home/jim/git/coris/pcb/lora-ets/lora-bom.csv") as reader:
    bom.read(reader)

with bomtool.CSVWriter("lora-bom-base.csv") as writer:
    bom.write(writer, [])

with bomtool.CSVWriter("lora-bom-cryo.csv") as writer:
    bom.write(writer, ['cryo'])