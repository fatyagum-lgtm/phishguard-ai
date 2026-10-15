PYTHON ?= python

.PHONY: install check ui serve demo smoke research
install:
	$(PYTHON) -m pip install -r requirements-lock.txt -e '.[dev]'
	npm ci --prefix frontend
check:
	ruff check src tests scripts
	ruff format --check src tests scripts
	$(PYTHON) -m pytest -q
	npm run format:check --prefix frontend
	npm run test --prefix frontend
	npm run build --prefix frontend
ui:
	npm run build --prefix frontend
serve:
	$(PYTHON) -m phishguard.cli serve
demo:
	$(PYTHON) scripts/demo.py
smoke:
	$(PYTHON) scripts/smoke_research.py --output reports/runs/smoke
research:
	$(PYTHON) -m phishguard.cli acquire
	$(PYTHON) -m phishguard.cli research --samples 40000 --seed 2026 --output reports/runs/reproduction
