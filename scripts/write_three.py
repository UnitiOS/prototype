"""Done condition for NEXT item 2: one script writes 1 intent + 3 assertions.

Run: .venv/Scripts/python.exe scripts/write_three.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "components" / "kernel"))

from perform import connect, perform  # noqa: E402


def main():
    with connect() as conn:
        intent_id, names, assertion_ids = perform(
            conn,
            actor_id="fareza",
            action_name="enrol_student",
            ontology_version="v0",
            note="first write through perform()",
            mint=["alice", "cohort_a", "has_name", "member_of", "enrolled_on"],
            assertions=[
                {
                    "subject": "alice",
                    "predicate": "has_name",
                    "value": "Alice Tan",
                    "valid_from": "2026-08-01T00:00:00Z",
                    "source": "human_stated",
                    "confidence": "high",
                },
                {
                    "subject": "alice",
                    "predicate": "member_of",
                    "ref": "cohort_a",
                    "valid_from": "2026-08-01T00:00:00Z",
                    "source": "human_stated",
                },
                {
                    "subject": "alice",
                    "predicate": "enrolled_on",
                    "value": "2026-08-01",
                    "valid_from": "2026-08-01T00:00:00Z",
                    "source": "document_extracted",
                    "confidence": "medium",
                    "authority": "registrar",
                },
            ],
        )

        print(f"intent    {intent_id}")
        for label, entity_id in names.items():
            print(f"entity    {entity_id}  {label}")

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT seq, value_literal, value_ref, valid_from, recorded_at,
                       source, ontology_version, subject_key_id
                FROM assertion WHERE intent_id = %s ORDER BY seq
                """,
                (intent_id,),
            )
            rows = cur.fetchall()

    for row in rows:
        print("assertion", row)
    assert len(rows) == 3, f"expected 3 assertions, got {len(rows)}"
    print(f"\nwrote 1 intent + {len(assertion_ids)} assertions")


if __name__ == "__main__":
    main()
