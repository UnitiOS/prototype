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

.PHONY: check venv db schema test replay dev-db dev-compile app web web-test web-dev eval eval-accountant

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

# ---------------------------------------------------------------- the application
# A development log of its own, never touched by the tests.
DEV_DB      := uniti_dev
DEV_OPS_DB  := uniti_dev_ops
DEV_DSN     := postgresql://uniti:uniti@localhost:5433/$(DEV_DB)
DEV_OPS_DSN := postgresql://uniti:uniti@localhost:5433/$(DEV_OPS_DB)
# Example modules are sealed here, beside the real store; the first root wins.
DEV_PACKAGES := build/dev/packages
DEV_STORE    := $(DEV_PACKAGES);packages
# The demonstration content: four modules and the facts stated under them.
# The same movements are stated twice, once in @demo/inventory's words and once
# in @rival/stock-moves', so the two applications can be compared on one log.
DEMO_DATA  := tests/modules/fixtures/demo_data.yaml
RIVAL_DATA := tests/modules/fixtures/rival_data.yaml
DEMO_APP   := $(DEV_PACKAGES)/@demo/stock/v2.yaml

# An empty development log, then the demonstration modules sealed into their
# own store root, then the facts. Empty to begin with is the point: everything
# the explorer shows afterwards was put there by a mechanism you can follow — a
# seal, a registration, a load, a form. Every one of those modules declares
# `purpose: demonstration`, and that word lands on every intent, so the log
# says of itself that its content is made up.
# 001_schema.sql drops the three tables first, so this replaces what was held.
dev-db: db venv
	@$(DC) exec -T db psql -U uniti -d postgres -tAc 	    "SELECT 1 FROM pg_database WHERE datname = '$(DEV_DB)'" | grep -q 1 	    || $(DC) exec -T db createdb -U uniti $(DEV_DB)
	MSYS_NO_PATHCONV=1 $(DC) exec -T db psql -U uniti -d $(DEV_DB) 	    -v ON_ERROR_STOP=1 -f /kernel/001_schema.sql
	UNITI_DSN=$(DEV_DSN) $(PY) scripts/dev_modules.py $(DEV_PACKAGES)
	UNITI_DSN=$(DEV_DSN) UNITI_PACKAGES="$(DEV_STORE)" 	    $(PY) scripts/load_facts.py $(DEMO_DATA) --actor dev
	UNITI_DSN=$(DEV_DSN) UNITI_PACKAGES="$(DEV_STORE)" 	    $(PY) scripts/load_facts.py $(RIVAL_DATA) --actor dev

# Compile every table the demonstration application can fill into an
# operational store of its own. The application only reads the log; this is the
# step that writes the derived tables, and it drops and rebuilds them whole.
dev-compile: venv
	@$(DC) exec -T db psql -U uniti -d postgres -tAc 	    "SELECT 1 FROM pg_database WHERE datname = '$(DEV_OPS_DB)'" | grep -q 1 	    || $(DC) exec -T db createdb -U uniti $(DEV_OPS_DB)
	UNITI_DSN=$(DEV_DSN) UNITI_OPS_DSN=$(DEV_OPS_DSN) UNITI_PACKAGES="$(DEV_STORE)" 	    $(PY) components/compiler/compile.py "$(DEMO_APP)" --into build/dev/projections

# The agent's eval, on the models config/agent.yaml names, over the development
# store (`make dev-db` first). Every task three times, one run at a time; a task
# passes when every run does. It calls the model, so it costs money: it stops at
# `--dollars` (0.50 unless said), prints a line per run, writes every call to
# build/calls and the report to build/evals.
# `EVAL_ARGS="--only on_hand --repeat 1 --dollars 0.15"` narrows.
EVAL_TASKS := tests/agent/evals/tasks.yaml

eval: venv
	UNITI_DSN=$(DEV_DSN) UNITI_PACKAGES="$(DEV_STORE)" 	    $(PY) -m components.agent eval $(EVAL_TASKS) --part builder $(EVAL_ARGS)

eval-accountant: venv
	$(PY) -m components.agent eval $(EVAL_TASKS) --part accountant $(EVAL_ARGS)

# Build the web application into web/dist, after its own tests: what the
# studio's map draws, what each thing is called, and where each box goes.
web:
	cd web && npm install --no-audit --no-fund && npm test && npm run build

web-test:
	cd web && npm test

# The API and the built application together, on http://localhost:8200.
# A request on the rehearsal's own module (@rehearsal/levels) is played from
# its script, one move every REHEARSAL_PAUSE seconds, with no model behind it:
# a way to watch the agent build on the map without spending anything.
REHEARSAL       ?= tests/agent/fixtures/rehearsal.yaml
REHEARSAL_PAUSE ?= 1.5
app: venv
	UNITI_AGENT_REHEARSAL=$(REHEARSAL) UNITI_AGENT_REHEARSAL_PAUSE=$(REHEARSAL_PAUSE) \
	UNITI_DSN=$(DEV_DSN) UNITI_OPS_DSN=$(DEV_OPS_DSN) UNITI_PACKAGES="$(DEV_STORE)" 	    $(PY) -m uvicorn components.api.app:app --port 8200

# While changing the frontend: Vite on http://localhost:5173, forwarding /api to `make app`.
web-dev:
	cd web && npm run dev
