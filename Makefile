# Uniti PoC. Run from the repo root, with the database up (docker compose up -d).

PY  := .venv/Scripts/python.exe
OUT := build

.PHONY: replay test

# Reset, seed 200 assertions, then rebuild the same projection twice and
# check the two are byte-identical. A projection is derived, never stored.
replay:
	$(PY) scripts/seed_200.py
	$(PY) scripts/project.py $(OUT)/projection_a.txt
	$(PY) scripts/project.py $(OUT)/projection_b.txt
	$(PY) scripts/project.py --compare $(OUT)/projection_a.txt $(OUT)/projection_b.txt

test:
	$(PY) -m pytest tests -q
