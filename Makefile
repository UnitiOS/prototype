# Uniti PoC. Run from the repo root.
# `make check` needs only Docker, Python 3.12 and a network connection —
# it builds the rest, including the virtualenv and the schema.

PY  := .venv/Scripts/python.exe
OUT := build
DC  := docker compose

# `make check` must not destroy evidence. `schema` drops and recreates the three
# tables and `replay` reseeds on top, so anything this file runs is run against a
# throwaway database — created if absent, wiped on every run. The working log is
# the default database in components/kernel/perform.py and is reached by running
# the scripts directly, never through make.
CHECK_DB := uniti_check
export UNITI_DSN := postgresql://uniti:uniti@localhost:5433/$(CHECK_DB)

.PHONY: check venv schema test replay check-profile

# The one command: environment, schema, tests, and a replay that must come out
# byte-identical twice. Exits non-zero if the tests fail or the two differ.
check: venv schema test replay
	@echo "check: ok"

venv: $(PY)

$(PY):
	python -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet "psycopg[binary]" pytest linkml

# Bring the server up if it is not, wait for it to accept connections, create the
# throwaway database if this is the first run, then apply the schema to it.
# 001_schema.sql drops and recreates: it is re-runnable.
schema:
	$(DC) up -d
	@n=0; until $(DC) exec -T db pg_isready -U uniti -d postgres >/dev/null 2>&1; do \
	    n=$$((n+1)); \
	    if [ $$n -ge 60 ]; then echo "database not ready after 60s"; exit 1; fi; \
	    sleep 1; \
	done
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(CHECK_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(CHECK_DB)
	MSYS_NO_PATHCONV=1 $(DC) exec -T db psql -U uniti -d $(CHECK_DB) \
	    -v ON_ERROR_STOP=1 -f /kernel/001_schema.sql

test: venv
	$(PY) -m pytest tests -q

# Cross-read the business profile: hold every section against every other one.
# It is not part of `check` — `check` builds and exercises the system, and this
# reads a description of a business. It needs no database and no schema.
check-profile: venv
	$(PY) scripts/check_profile.py

# Reset, seed 200 assertions, then rebuild the same projection twice and
# check the two are byte-identical. A projection is derived, never stored.
replay: venv
	$(PY) scripts/seed_200.py
	$(PY) scripts/project.py $(OUT)/projection_a.txt
	$(PY) scripts/project.py $(OUT)/projection_b.txt
	$(PY) scripts/project.py --compare $(OUT)/projection_a.txt $(OUT)/projection_b.txt
