"""Build one projection by replaying the log.

A projection is derived, never stored. It is not written back as assertions:
it is rebuilt from `assertion` every time, by asking resolve_single() for the
winner of every (subject, predicate) pair at one pair of clocks.

Labels come from the log too. The `has_label` predicate is the one entity that
labels itself, so the projection needs no lookup table outside the kernel.

Run: .venv/Scripts/python.exe scripts/project.py build/projection_a.txt
     .venv/Scripts/python.exe scripts/project.py --compare FILE FILE
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kernel"))

from perform import connect  # noqa: E402
from resolve import resolve_single  # noqa: E402

VALID_AT = "2026-06-01T00:00:00Z"
AS_OF = "2026-12-31T00:00:00Z"

# The predicate that names things is the one that names itself.
_HAS_LABEL_SQL = """
SELECT DISTINCT subject_id FROM assertion
WHERE subject_id = predicate_id AND value_literal = 'has_label'
"""

_PAIRS_SQL = "SELECT DISTINCT subject_id, predicate_id FROM assertion"

_HEADERS = ("subject", "predicate", "value", "valid_from", "recorded_at",
            "seq", "source")


def build(conn):
    """Return the projection as a list of tuples, deterministically ordered."""
    with conn.cursor() as cur:
        cur.execute(_HAS_LABEL_SQL)
        (has_label,) = cur.fetchone()
        cur.execute(_PAIRS_SQL)
        pairs = cur.fetchall()

    def label_of(entity_id):
        row = resolve_single(conn, subject_id=entity_id,
                             predicate_id=has_label,
                             valid_at=VALID_AT, as_of=AS_OF)
        return row["value_literal"] if row else f"<{entity_id}>"

    labels = {}
    for subject_id, predicate_id in pairs:
        for entity_id in (subject_id, predicate_id):
            if entity_id not in labels:
                labels[entity_id] = label_of(entity_id)

    out = []
    for subject_id, predicate_id in pairs:
        row = resolve_single(conn, subject_id=subject_id,
                             predicate_id=predicate_id,
                             valid_at=VALID_AT, as_of=AS_OF)
        if row is None:
            continue
        if row["value_ref"] is not None:
            if row["value_ref"] not in labels:
                labels[row["value_ref"]] = label_of(row["value_ref"])
            value = "-> " + labels[row["value_ref"]]
        else:
            value = row["value_literal"]
        out.append((
            labels[subject_id],
            labels[predicate_id],
            value,
            row["valid_from"].date().isoformat(),
            row["recorded_at"].date().isoformat(),
            str(row["seq"]),
            row["source"],
            str(subject_id),
        ))

    out.sort()
    return [row[:-1] for row in out]


def render(rows):
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(_HEADERS)]

    def line(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    body = [
        f"projection: current value per (subject, predicate)",
        f"valid_at   {VALID_AT}",
        f"as_of      {AS_OF}",
        "",
        line(_HEADERS),
        line(["-" * w for w in widths]),
    ]
    body.extend(line(r) for r in rows)
    body.append("")
    body.append(f"{len(rows)} rows")
    return "\n".join(body) + "\n"


def compare(path_a, path_b):
    a, b = Path(path_a).read_bytes(), Path(path_b).read_bytes()
    if a != b:
        print(f"replay is NOT deterministic: {path_a} != {path_b}")
        return 1
    print(f"replay is identical twice in a row: "
          f"{path_a} == {path_b} ({len(a)} bytes)")
    return 0


def main(argv):
    if argv[:1] == ["--compare"]:
        return compare(argv[1], argv[2])

    out = Path(argv[0]) if argv else None
    with connect() as conn:
        text = render(build(conn))
    if out is None:
        sys.stdout.write(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out} ({len(text.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
