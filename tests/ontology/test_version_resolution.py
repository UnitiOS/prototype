"""Which map version applies at (valid_at, as_of), proved from files alone.

Two fixture directories, both a handful of lines:

    chain/        v1 valid 1 Jan, sealed 1 Jan · v2 valid 1 Feb, sealed 1 Feb
                  plus a draft.yaml that is not sealed and must not be read
    retroactive/  v1 valid 1 Jan, sealed 1 Jan · v2 valid 1 Jan, sealed 1 Mar
    reseal/       chain/ plus a v3 valid 1 Jan, sealed 1 Mar — a rewrite that
                  re-claims January, so the version sealed last is not the one
                  with the latest valid_from

`chain` is an ordinary forward chain: each version starts when it was sealed.
`retroactive` is a correction to a definition — v2 claims the period v1 already
claimed, and was written two months later. `reseal` is the only fixture that
tells the rule apart from the kernel's: ordering on valid_from would answer v2
where the rule answers v3.

Run: .venv/Scripts/python.exe -m pytest tests/ontology -q
"""

import sys
from pathlib import Path

# `components` rather than `components/ontology`: the kernel has a resolve.py
# too, and both on sys.path as top-level modules would hand back whichever
# pytest imported first.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "components"))

from ontology.resolve import resolve_version  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CHAIN = FIXTURES / "chain"
RETROACTIVE = FIXTURES / "retroactive"
RESEAL = FIXTURES / "reseal"


def test_a_version_sealed_after_as_of_is_invisible():
    """v2 is valid on 1 March, but on 15 January nobody had written it yet."""
    winner = resolve_version(CHAIN, valid_at="2026-03-01T00:00:00Z",
                             as_of="2026-01-15T00:00:00Z")
    assert winner["version"] == "v1"


def test_among_the_versions_valid_at_valid_at_the_one_sealed_last_wins():
    """Both v1 and v2 are valid on 1 March. The later seal supersedes."""
    winner = resolve_version(CHAIN, valid_at="2026-03-01T00:00:00Z",
                             as_of="2026-04-01T00:00:00Z")
    assert winner["version"] == "v2"
    assert winner["supersedes"] == "v1"
    assert winner["path"].name == "v2.yaml"


def test_sealed_last_wins_even_when_another_version_starts_later():
    """The clause is sealed_at, not valid_from — the kernel's rule differs here.

    v2 starts on 1 February and v3 on 1 January, so the latest-starting version
    is v2. v3 was sealed a month after it, and supersedes it whole.
    """
    winner = resolve_version(RESEAL, valid_at="2026-04-01T00:00:00Z",
                             as_of="2026-04-01T00:00:00Z")
    assert winner["version"] == "v3"


def test_a_retroactive_version_beats_the_one_it_supersedes():
    """Same valid_at, same valid_from. Only sealed_at separates the two."""
    winner = resolve_version(RETROACTIVE, valid_at="2026-01-15T00:00:00Z",
                             as_of="2026-04-01T00:00:00Z")
    assert winner["version"] == "v2"


def test_the_superseded_version_still_stands_before_its_correction():
    """The same valid_at, read a month before the correction was sealed."""
    winner = resolve_version(RETROACTIVE, valid_at="2026-01-15T00:00:00Z",
                             as_of="2026-02-01T00:00:00Z")
    assert winner["version"] == "v1"


def test_an_as_of_before_the_first_seal_returns_nothing():
    """Not an error: on that date the business had not been described yet."""
    assert resolve_version(CHAIN, valid_at="2026-03-01T00:00:00Z",
                           as_of="2025-12-01T00:00:00Z") is None


def test_a_valid_at_before_the_first_version_returns_nothing():
    """Every version is visible, and none of them claims December."""
    assert resolve_version(CHAIN, valid_at="2025-12-01T00:00:00Z",
                           as_of="2026-04-01T00:00:00Z") is None
