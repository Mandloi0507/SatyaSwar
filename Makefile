.PHONY: setup test mock serve stream export-schemas eval lint

setup:
	pip install -e .

test:
	pytest -v

mock:
	python -m satyaswar_ml.adapters.ws_app

serve:
	uvicorn satyaswar_ml.adapters.ws_app:app --host 127.0.0.1 --port 8100 --reload

stream:
	python scripts/stream_wav.py

export-schemas:
	python scripts/export_schemas.py

eval:
	python eval/run_eval.py

lint:
	ruff check src tests configs
