# Uniti PoC. Run from the repo root.
# `make check` needs only Docker, Python 3.12 and a network connection —
# it builds the rest, including the virtualenv and the schema.

PY  := .venv/Scripts/python.exe
# `build/check/` is what `make check` writes and holds nothing else; the
# renders a person looks at live under `build/<business>/<version>/`.
OUT := build/check
DC  := docker compose

# `make check` must not destroy evidence. `schema` drops and recreates the three
# tables and `replay` reseeds on top, so anything this file runs is run against a
# throwaway database — created if absent, wiped on every run. The working log is
# the default database in components/kernel/perform.py and is reached by running
# the scripts directly, never through make.
CHECK_DB := uniti_check
export UNITI_DSN := postgresql://uniti:uniti@localhost:5433/$(CHECK_DB)

# What `make build` renders, and where it puts it.
BUSINESS := sorella
VERSION  := v3
MAP      := business/$(BUSINESS)/$(VERSION).yaml
RENDER   := build/$(BUSINESS)/$(VERSION)
GRAPH    := build/$(BUSINESS)/$(VERSION)/graph/$(BUSINESS)-$(VERSION)

# The operational database. A store of its own and not a schema inside the log:
# a read path from a form to `assertion` is then impossible rather than
# discouraged. It is derived, so it is dropped and rebuilt on every run.
OPS_DB := uniti_ops

# The port `make serve` listens on.
PORT   := 8000

.PHONY: check venv schema test replay check-profile build compile serve \
        demo-seed demo-serve

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

# The inspection surface: the map, rendered for a person to look at. It is
# deliberately not a part of `check` — check exercises the system and can fail,
# build only renders. It reads the working log, never the throwaway one, so it
# overrides the DSN this file exports; it writes nothing back.
# pyLODE is absent on purpose: it is being tried, not adopted.
build: export UNITI_DSN := postgresql://uniti:uniti@localhost:5433/uniti
build: venv
	$(DC) up -d
	mkdir -p $(RENDER)/graph $(RENDER)/forms $(RENDER)/tables $(RENDER)/log
	PYTHONIOENCODING=utf-8 .venv/Scripts/gen-owl.exe --no-use-native-uris $(MAP) > $(GRAPH).raw.ttl 2> $(RENDER)/log/gen-owl.err
	PYTHONIOENCODING=utf-8 $(PY) scripts/owl_domains.py $(GRAPH).raw.ttl --out $(GRAPH).ttl 2> $(RENDER)/log/owl_domains.err
	PYTHONIOENCODING=utf-8 $(PY) scripts/render_map.py $(MAP) table --into $(RENDER)/tables 2> $(RENDER)/log/tables.err
	PYTHONIOENCODING=utf-8 $(PY) scripts/render_map.py $(MAP) form --into $(RENDER)/forms 2> $(RENDER)/log/forms.err
	@echo "build: $(RENDER)"

# The map's rules, executed. Like `build` it reads the working log rather than
# the throwaway one, because that is where the day being entered lives, and it
# writes only to the operational store — which it creates on the first run and
# drops table by table on every run after.
compile: export UNITI_DSN     := postgresql://uniti:uniti@localhost:5433/uniti
compile: export UNITI_OPS_DSN := postgresql://uniti:uniti@localhost:5433/$(OPS_DB)
compile: venv
	$(DC) up -d
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(OPS_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(OPS_DB)
	mkdir -p $(RENDER)/tables $(RENDER)/log
	PYTHONIOENCODING=utf-8 $(PY) components/compiler/compile.py $(MAP) \
	    --into $(RENDER)/tables 2> $(RENDER)/log/compile.err

# The loop, in a browser. Four routes over the map, the trial log and an
# operational store of its own — deliberately not $(OPS_DB), which `make
# compile` drops and rebuilds from the working log; a page rebuilding a table
# on every load must not collide with it. Created on first run, like that one.
TRIAL_DB     := uniti_trial
TRIAL_OPS_DB := uniti_trial_ops

serve: export UNITI_DSN     := postgresql://uniti:uniti@localhost:5433/$(TRIAL_DB)
serve: export UNITI_OPS_DSN := postgresql://uniti:uniti@localhost:5433/$(TRIAL_OPS_DB)
serve: venv
	$(DC) up -d
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(TRIAL_OPS_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(TRIAL_OPS_DB)
	PYTHONIOENCODING=utf-8 $(PY) components/web/serve.py $(MAP) --port $(PORT)

# ---- the demonstration business -------------------------------------------
# Its own map, its own log and its own operational store, so that seeding it
# from empty touches neither the working log nor the trial one. The seed is
# dated in the past and rerunnable: it drops the three tables and writes them
# again through the same write gate a form writes through.
DEMO_BUSINESS := sorella_demo
DEMO_MAP      := business/$(DEMO_BUSINESS)/v1.yaml
DEMO_DB       := uniti_demo
DEMO_OPS_DB   := uniti_demo_ops
DEMO_DSN      := postgresql://uniti:uniti@localhost:5433/$(DEMO_DB)
DEMO_OPS_DSN  := postgresql://uniti:uniti@localhost:5433/$(DEMO_OPS_DB)
# What the compiler printed, kept where a person looks at what came out.
DEMO_RENDER   := build/$(DEMO_BUSINESS)/v1/tables.txt

# Seed, then compile — in that order and both here, because the forms read
# their choices out of the operational store and a store nothing has filled
# offers nothing. `compile.py` with no class named fills every table the map
# can fill: the two groupings, and one list per class the log can say an
# entity is of.
demo-seed: export UNITI_DSN     := $(DEMO_DSN)
demo-seed: export UNITI_OPS_DSN := $(DEMO_OPS_DSN)
demo-seed: venv
	$(DC) up -d
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(DEMO_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(DEMO_DB)
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(DEMO_OPS_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(DEMO_OPS_DB)
	mkdir -p $(dir $(DEMO_RENDER))
	PYTHONIOENCODING=utf-8 $(PY) scripts/seed_demo.py
	PYTHONIOENCODING=utf-8 $(PY) components/compiler/compile.py $(DEMO_MAP) \
	    > $(DEMO_RENDER)
	@echo "demo-seed: $(DEMO_DB), tables in $(DEMO_OPS_DB), $(DEMO_RENDER)"

demo-serve: export UNITI_DSN     := $(DEMO_DSN)
demo-serve: export UNITI_OPS_DSN := $(DEMO_OPS_DSN)
demo-serve: venv
	$(DC) up -d
	@$(DC) exec -T db psql -U uniti -d postgres -tAc \
	    "SELECT 1 FROM pg_database WHERE datname = '$(DEMO_OPS_DB)'" | grep -q 1 \
	    || $(DC) exec -T db createdb -U uniti $(DEMO_OPS_DB)
	PYTHONIOENCODING=utf-8 $(PY) components/web/serve.py $(DEMO_MAP) --port $(PORT)
