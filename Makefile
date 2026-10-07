PY ?= .venv/bin/python
export PYTHONPATH := $(CURDIR)

.PHONY: setup lca verify run rebuild test lint dbt app

setup:            ## create .venv (Python 3.11) and install everything
	~/.pyenv/versions/3.11.9/bin/python -m venv .venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements-dev.txt

lca:              ## download FY LCA files (needs playwright) and rebuild data/lca/*.parquet
	$(PY) -m pip install playwright && $(PY) -m playwright install chromium
	$(PY) scripts/fetch_lca.py --fy 2025
	$(PY) -m pipeline.lca

verify:           ## re-verify candidate job-board tokens -> seeds/companies.csv
	$(PY) -m pipeline.verify_companies

run:              ## full daily pipeline: ingest -> dbt build -> export
	$(PY) -m pipeline.run

rebuild:          ## dbt build + export from the latest local snapshot (no fetching)
	$(PY) -m pipeline.run --skip-ingest

dbt:
	.venv/bin/dbt build --project-dir dbt --profiles-dir dbt

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

app:
	.venv/bin/streamlit run app/streamlit_app.py
