all:
	mypy -p bomtool

	cp ~/git/coris/pcb/lora-ets/lora-bom.ods lora-bom.ods
	cp ~/git/coris/pcb/lora-ets/lora.sch lora.sch
	cp ~/git/coris/pcb/lora-ets/lora.brd lora.brd

	@echo "-- extract ODS to CSV, should be same as ssconvert"
	./bomtool.py -i lora-bom.ods -o lora-bom.csv
	ssconvert lora-bom.ods lora-bom2.csv
	diff -u lora-bom.csv lora-bom2.csv

	@echo "-- extract variants"
	./bomtool.py -i lora-bom.ods -o lora-bom-base.csv -v base
	./bomtool.py -i lora-bom.ods -o lora-bom-foo.csv -v foo
	./bomtool.py -i lora-bom.ods -o lora-bom-cryo.csv -v cryo
	diff -u lora-bom-base.csv lora-bom-foo.csv
	! diff -q lora-bom-base.csv lora-bom-cryo.csv

	@echo "-- extracting again should be the same"

	./bomtool.py -i lora-bom-base.csv -o lora-bom-base2.csv
	diff -u lora-bom-base.csv lora-bom-base2.csv

	./bomtool.py -i lora-bom-base.csv -o lora-bom-base3.csv -v base
	diff -u lora-bom-base.csv lora-bom-base3.csv

	./bomtool.py -i lora-bom-base.csv -o lora-bom-base4.csv -v cryo
	diff -u lora-bom-base.csv lora-bom-base4.csv

	@echo "-- export ODS"
	./bomtool.py -i lora-bom.ods -o lora-bom.ods
	./bomtool.py -i lora-bom.ods -o lora-bom-base.ods -v base
	./bomtool.py -i lora-bom.ods -o lora-bom-cryo.ods -v cryo

	@echo "-- inject into to Eagle files"
	cp lora.sch lora-all.sch
	cp lora.brd lora-all.brd
	./bomtool.py -i lora-bom.ods -O lora-all.sch lora-all.brd

	cp lora.sch lora-base.sch
	cp lora.brd lora-base.brd
	./bomtool.py -i lora-bom.ods -O lora-base.sch lora-base.brd -v base

	cp lora.sch lora-cryo.sch
	cp lora.brd lora-cryo.brd
	./bomtool.py -i lora-bom.ods -O lora-cryo.sch lora-cryo.brd -v cryo

	@echo "-- extract from Eagle files"
	./bomtool.py -I lora-all.sch lora-all.brd -o lora-bom-extract.csv

	./bomtool.py -I lora-all.sch lora-all.brd -o lora-bom-extract-value.csv --eagle-value
	! diff -q lora-bom-extract.csv lora-bom-extract-value.csv

	./bomtool.py -I lora-all.sch lora-all.brd -o lora-bom-extract-base.csv -v base
	./bomtool.py -I lora-base.sch lora-base.brd -o lora-bom-extract-base2.csv

	./bomtool.py -I lora-all.sch lora-all.brd -o lora-bom-extract-cryo.csv -v cryo
	./bomtool.py -I lora-cryo.sch lora-cryo.brd -o lora-bom-extract-cryo2.csv

	diff -u lora-bom.csv lora-bom-extract.csv
	diff -u lora-bom-base.csv lora-bom-extract-base.csv
	diff -u lora-bom-base.csv lora-bom-extract-base2.csv
	diff -u lora-bom-cryo.csv lora-bom-extract-cryo.csv
	diff -u lora-bom-cryo.csv lora-bom-extract-cryo2.csv

clean::
	rm -f lora*
