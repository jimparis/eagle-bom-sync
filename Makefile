T=lora

def:
	mypy -p bomtool
	./bomtool.py -i ~/git/coris/pcb/lora-ets/lora-bom.ods -o lora-bom.csv
	./bomtool.py -i ~/git/coris/pcb/lora-ets/lora-bom.ods -o lora-bom-base.csv -v base
	./bomtool.py -i ~/git/coris/pcb/lora-ets/lora-bom.ods -o lora-bom-cryo.csv -v cryo
	./bomtool.py -i ~/git/coris/pcb/lora-ets/lora-bom.ods -o lora-bom.ods
	./bomtool.py -i ~/git/coris/pcb/lora-ets/lora-bom.ods -o lora-bom-base.ods -v base
	./bomtool.py -i ~/git/coris/pcb/lora-ets/lora-bom.ods -o lora-bom-cryo.ods -v cryo
#	./test.py

#	ssconvert ~/git/coris/pcb/lora-ets/lora-bom.ods lora-bom.csv
#	mypy -p bomtool
#	./test.py

all:
	./eagle-bom-sync.py -i $T-bom.csv $T.sch $T.brd
	./eagle-bom-sync.py -e $T.sch $T.brd > all.csv
	./eagle-bom-sync.py --variant base -e $T.sch $T.brd > base.csv
	./eagle-bom-sync.py --variant cryo -e $T.sch $T.brd > cryo1.csv
	./eagle-bom-sync.py --variant cryo,cryo_vusb -e $T.sch $T.brd > cryo2.csv
