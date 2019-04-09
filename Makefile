T=~/git/micro1v8/hardware/micro1v8

all:
	./eagle-bom-sync.py -i $T-bom.csv $T.sch $T.brd
	./eagle-bom-sync.py -e $T.sch $T.brd > test1.csv
