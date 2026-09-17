# Uniti PoC. Run from the repo root.
# `make check` needs only Docker, Python 3.12 and a network connection.

PY := .venv/Scripts/python.exe
DC := docker compose

# Everything `make` runs goes against throwaway databases: the schema is
# re-applied (which drops the log) and projections are dropped and rebuilt.
CHECK_DB     := uniti_check
CHECK_OPS_DB := uniti_check_ops
export UNITI_DSN     := postgresql://uniti:uniti@localhost:5433/$(CHECK_DB)
export UNITI_OPS_DSN := postgresql://uniti:uniti@localhost:5433/$(CHECK_OPS_DB)

OUT := build/check

.PHONY: check venv db schema test replay

# Environment, schema, tests, and a replay that must come out byte-identical twice.
check: venv schema test replay
	@echo "check: ok"

venv: $(PY)

$(PY):
	python -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet "psycopg[binary]" pytest linkml

# Bring the database server up and wait until it accepts connections.
db:
	$(DC) up -d
	@n=0; until $(DC) exec -T db pg_isready -U uniti -d postgres >/dev/null 2>&1; do \
	    n=$$((n+1)); \
	    if [ $$n -ge 60 ]; then echo "database not ready after 60s"; exit 1; fi; \
	    sleep 1; \
	done

# Create the throwaway log if absent, then apply the kernel schema to it.
schema: db
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(CHECK_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(CHECK_DB)
	MSYS_NO_PATHCONV=1 $(DC) exec -T db psql -U uniti -d $(CHECK_DB) \
	    -v ON_ERROR_STOP=1 -f /kernel/001_schema.sql

test: venv
	$(PY) -m pytest tests -q

# Seed 200 assertions, rebuild the same projection twice, and require the two
# to be byte-identical. A projection is derived, never stored.
replay: venv
	@mkdir -p $(OUT)
	$(PY) scripts/seed_200.py
	$(PY) scripts/project.py $(OUT)/projection_a.txt
	$(PY) scripts/project.py $(OUT)/projection_b.txt
	$(PY) scripts/project.py --compare $(OUT)/projection_a.txt $(OUT)/projection_b.txt
