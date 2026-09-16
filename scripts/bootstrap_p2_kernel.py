"""Bootstrap the Prototype 2 Kernel Database (uniti_p2).

This script initializes the clean-slate Prototype 2 kernel database:
1. Connects to PostgreSQL and ensures the `uniti_p2` database exists.
2. Applies `components/kernel/001_schema.sql` (creating intent, entity, assertion).
3. Registers ONLY the foundational ontologies from `@uniti/core`:
   - `packages/@uniti/core/schema/archetypes.yaml` (5 foundational archetypes)
   - `packages/@uniti/core/schema/base_types.yaml` (Person, Organization, PhysicalLocation)
4. Enforces zero operational seed data and zero community modules.

Usage:
    .venv/Scripts/python.exe scripts/bootstrap_p2_kernel.py
    .venv/Scripts/python.exe scripts/bootstrap_p2_kernel.py --dsn postgresql://uniti:uniti@localhost:5433/uniti_p2
"""

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from seal import register  # noqa: E402

DEFAULT_DSN = os.environ.get(
    "UNITI_P2_KERNEL_DSN",
    os.environ.get("UNITI_KERNEL_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_p2"),
)

SCHEMA_SQL = ROOT / "components" / "kernel" / "001_schema.sql"
ARCHETYPES_PATH = ROOT / "packages" / "@uniti" / "core" / "schema" / "archetypes.yaml"
BASE_TYPES_PATH = ROOT / "packages" / "@uniti" / "core" / "schema" / "base_types.yaml"


def get_admin_dsn(p2_dsn: str) -> str:
    """Derive admin connection DSN (connecting to postgres default DB) to create uniti_p2."""
    parsed = urlparse(p2_dsn)
    # Replace path with /postgres
    admin_parts = parsed._replace(path="/postgres")
    return urlunparse(admin_parts)


def get_db_name(dsn: str) -> str:
    parsed = urlparse(dsn)
    return parsed.path.lstrip("/") or "uniti_p2"


def ensure_p2_database(dsn: str) -> None:
    """Ensure the target database exists; create it if absent."""
    dbname = get_db_name(dsn)
    admin_dsn = get_admin_dsn(dsn)
    
    print(f"Checking database '{dbname}' via admin connection...")
    try:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if not cur.fetchone():
                    print(f"Creating database '{dbname}'...")
                    cur.execute(f'CREATE DATABASE "{dbname}"')
                    print(f"Database '{dbname}' created successfully.")
                else:
                    print(f"Database '{dbname}' already exists.")
    except Exception as exc:
        # If admin connection to /postgres fails, try connecting directly to target DB
        print(f"Notice: Admin check returned: {exc}. Attempting direct connect...")


def reset_schema(conn) -> None:
    """Drop and recreate kernel tables (intent, entity, assertion) with triggers."""
    print("Applying kernel schema DDL (components/kernel/001_schema.sql)...")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.autocommit = False
    print("Kernel schema applied cleanly.")


def bootstrap_kernel(dsn: str, actor_id: str = "uniti_system") -> dict:
    """Bootstrap uniti_p2 kernel with pure foundational ontology."""
    ensure_p2_database(dsn)

    print(f"Connecting to P2 kernel at: {dsn}")
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        reset_schema(conn)

        # 1. Register foundational archetypes
        print(f"\nRegistering {ARCHETYPES_PATH.name}...")
        res_archetypes = register(conn, ARCHETYPES_PATH, actor_id=actor_id)
        print(f"  Version: {res_archetypes['version']}")
        archetype_keys = list(res_archetypes['minted'])
        print(f"  Minted URIs ({len(archetype_keys)}): {', '.join(archetype_keys[:6])}...")

        # 2. Register standard base types
        print(f"\nRegistering {BASE_TYPES_PATH.name}...")
        res_base_types = register(conn, BASE_TYPES_PATH, actor_id=actor_id)
        print(f"  Version: {res_base_types['version']}")
        base_keys = list(res_base_types['minted'])
        print(f"  Minted URIs ({len(base_keys)}): {', '.join(base_keys[:6])}...")

        # 3. Verify clean state
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM intent")
            intent_count = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM entity")
            entity_count = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM assertion")
            assertion_count = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM assertion WHERE source != 'system_derived'")
            operational_facts = cur.fetchone()[0]

            # List all registered classes and slots
            cur.execute("""
                SELECT value_literal 
                FROM assertion 
                WHERE subject_id = predicate_id 
                   OR predicate_id = (SELECT subject_id FROM assertion WHERE value_literal = 'uniti:uri' ORDER BY seq LIMIT 1)
                ORDER BY seq
            """)
            registered_uris = [row[0] for row in cur.fetchall() if row[0]]

        print("\n" + "=" * 60)
        print("PROTOTYPE 2 KERNEL BOOTSTRAP COMPLETE")
        print("=" * 60)
        print(f"Database:                {get_db_name(dsn)}")
        print(f"Intents:                 {intent_count}")
        print(f"Registered Entities:     {entity_count}")
        print(f"Total Assertions:        {assertion_count}")
        print(f"Operational Facts:       {operational_facts} (Zero operational seed data)")
        print(f"Ontology Scope:          @uniti/core only (No community/tenant data)")
        print(f"Distinct Registered URIs: {len(set(registered_uris))}")
        print("=" * 60)

        assert operational_facts == 0, f"Expected 0 operational facts, got {operational_facts}"
        return {
            "status": "success",
            "database": get_db_name(dsn),
            "archetypes": res_archetypes,
            "base_types": res_base_types,
            "entity_count": entity_count,
            "assertion_count": assertion_count,
            "operational_facts": operational_facts,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bootstrap clean-slate Prototype 2 Kernel database with @uniti/core ontologies."
    )
    parser.add_argument(
        "--dsn",
        default=DEFAULT_DSN,
        help=f"Kernel database DSN (default: {DEFAULT_DSN})",
    )
    parser.add_argument(
        "--actor",
        default="uniti_system",
        help="Actor ID performing the bootstrap registration (default: uniti_system)",
    )
    args = parser.parse_args(argv)

    try:
        bootstrap_kernel(args.dsn, actor_id=args.actor)
        return 0
    except psycopg.OperationalError as exc:
        print(f"\n[ERROR] Could not connect to PostgreSQL at {args.dsn}: {exc}", file=sys.stderr)
        print("Make sure PostgreSQL is running (e.g. docker compose up -d) on port 5433.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"\n[ERROR] Bootstrap failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
