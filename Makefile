PY ?= python3
CONFIG ?= configs/default.yaml

.PHONY: bench smoke tables test images install
install:
	$(PY) -m pip install -r requirements.txt
images:
	$(PY) scripts/fetch_images.py
pull:
	grep -o 'tag: "[^"]*"' $(CONFIG) | cut -d'"' -f2 | xargs -n1 ollama pull
bench: images
	$(PY) -m bakeoff.run $(CONFIG)
	$(PY) -m bakeoff.tables results/runs
smoke:
	$(PY) -m bakeoff.run configs/smoke.yaml --out results/smoke
tables:
	$(PY) -m bakeoff.tables results/legacy results/runs
test:
	$(PY) -m pytest -q
