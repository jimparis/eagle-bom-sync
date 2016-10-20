all:
	./eagle-bom-sync.py -i ~/git/micro1v8/micro1v8-bom.csv ~/git/micro1v8/micro1v8.brd
	./eagle-bom-sync.py -e ~/git/micro1v8/micro1v8.brd > test1.csv
