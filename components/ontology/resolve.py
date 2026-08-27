"""resolve_version() — which map version applies at (valid_at, as_of).

A directory of sealed files in, one version out. Pure: no database, no LinkML
runtime, nothing written. The rule is the 2026-08-26 line in DECISIONS.md and
nothing more:

    among versions with sealed_at <= :as_of, take those with
    valid_from <= :valid_at, then the one sealed last.

Note what is *not* in it. The kernel orders on max valid_from first and only
then on record time; the map orders on sealed_at alone. A fact is one claim
among many that vary over valid time, so the latest-starting one wins. A map
version applies whole — the later seal supersedes the earlier one whatever
period it claims — which is what makes a retroactive correction to a definition
beat the definition it replaces at the same valid_at.

Version metadata lives in the schema's own `annotations` block: valid_from,
sealed_at, supersedes, transcript. That is four keys of plain YAML, so this
file reads them itself rather than taking a dependency to do it. The reader is
deliberately shallow — top-level scalars and the immediate children of
`annotations`, in the simple `key: value` form. Anything nested deeper is
skipped, because nothing here needs it.

A sealed version is `vN.yaml`. `draft.yaml` is not sealed and is not read.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

# Top-level scalars and one nested block are all the shapes this reads.
_KEY = re.compile(r"^(?P<indent> *)(?P<key>[A-Za-z_][A-Za-z0-9_-]*):[ \t]*(?P<value>.*)$")


def _scalar(text):
    """A YAML scalar, as far as four metadata keys need one."""
    text = text.strip()
    if text in ("", "null", "~"):
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _instant(value):
    """An ISO 8601 string or a datetime, as one aware datetime.

    A naive input is read as UTC: the fixtures and the seal tool both write Z,
    and a comparison that raises on a missing suffix would be the only way this
    function can fail on well-formed input.
    """
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def _read_header(path):
    """Top-level keys and the annotations block of one schema file."""
    top, annotations, inside = {}, {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _KEY.match(line)
        if match is None:          # list items, block scalars, continuations
            continue
        key, value = match["key"], _scalar(match["value"])
        if len(match["indent"]) == 0:
            inside = key == "annotations"
            if value is not None:
                top[key] = value
        elif inside:
            annotations[key] = value
    return top, annotations


def _require(path, key, value):
    if value is None:
        raise ValueError(f"{path.name}: sealed version has no {key}")
    return value


def load_versions(directory):
    """Every sealed version in `directory`, in filename order.

    The version's own name comes from inside the file, never from the filename
    and never from git — the 2026-08-26 line in DECISIONS.md. A file that does
    not carry the three keys this needs is malformed, and says so by name.
    """
    versions = []
    for path in sorted(Path(directory).glob("v*.yaml")):
        top, annotations = _read_header(path)
        versions.append(
            {
                "version": _require(path, "version", top.get("version")),
                "path": path,
                "valid_from": _instant(
                    _require(path, "valid_from", annotations.get("valid_from"))
                ),
                "sealed_at": _instant(
                    _require(path, "sealed_at", annotations.get("sealed_at"))
                ),
                "supersedes": annotations.get("supersedes"),
                "transcript": annotations.get("transcript"),
            }
        )
    return versions


def resolve_version(directory, *, valid_at, as_of):
    """Return the winning version as a dict, or None if none applies.

    None is the honest answer for an as_of before the first seal: at that
    moment the business had not been described yet, which is a fact about the
    map, not an error in the call.
    """
    valid_at, as_of = _instant(valid_at), _instant(as_of)
    candidates = [
        v
        for v in load_versions(directory)
        if v["sealed_at"] <= as_of and v["valid_from"] <= valid_at
    ]
    if not candidates:
        return None
    # Stable sort, so two versions sharing a sealed_at fall back to filename
    # order — determinism, not a rule. Seals are sequential acts.
    candidates.sort(key=lambda v: v["sealed_at"])
    return candidates[-1]
