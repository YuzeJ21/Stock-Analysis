.PHONY: test pipeline daily dashboard

test:
	python3 -m pytest tests -q

pipeline:
	python3 -m src.report_generator

daily:
	python3 -m src.data_update
	python3 -m src.report_generator
	python3 -m src.monthly_picks --generate --top-n 5
	python3 -m src.track_record --monthly-picks
	python3 -m src.stock_report --validate-local-data

dashboard:
	streamlit run src/dashboard.py
