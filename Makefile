# Uniti PoC. Run from the repo root.
# `make check` needs only Docker, Python 3.12 and a network connection —
# it builds the rest, including the virtualenv and the schema.

PY  := .venv/Scripts/python.exe
OUT := build
DC  := docker compose

.PHONY: check venv schema test replay

# The one command: environment, schema, tests, and a replay that must come out
# byte-identical twice. Exits non-zero if the tests fail or the two differ.
check: venv schema test replay
	@echo "check: ok"

venv: $(PY)

$(PY):
	python -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet "psycopg[binary]" pytest linkml

# Bring the database up if it is not, wait for it to accept connections, then
# apply the schema. 001_schema.sql drops and recreates: it is re-runnable.
schema:
	$(DC) up -d
	@n=0; until $(DC) exec -T db pg_isready -U uniti -d uniti >/dev/null 2>&1; do \
	    n=$$((n+1)); \
	    if [ $$n -ge 60 ]; then echo "database not ready after 60s"; exit 1; fi; \
	    sleep 1; \
	done
	MSYS_NO_PATHCONV=1 $(DC) exec -T db psql -U uniti -d uniti \
	    -v ON_ERROR_STOP=1 -f /kernel/001_schema.sql

test: venv
	$(PY) -m pytest tests -q

# Reset, seed 200 assertions, then rebuild the same projection twice and
# check the two are byte-identical. A projection is derived, never stored.
replay: venv
	$(PY) scripts/seed_200.py
	$(PY) scripts/project.py $(OUT)/projection_a.txt
	$(PY) scripts/project.py $(OUT)/projection_b.txt
	$(PY) scripts/project.py --compare $(OUT)/projection_a.txt $(OUT)/projection_b.txt
