#T=~/git/micro1v8/micro1v8
T=~/git/bolt/vergesense/sensor-hardware/poe/sensor

all:
	./eagle-bom-sync.py -i $T-bom.csv $T.sch $T.brd
	./eagle-bom-sync.py -e $T.sch $T.brd > test1.csv
