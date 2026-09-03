# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. This file had grown to
thirty finished items and two live ones, which is a log wearing a to-do list's
name.

The profile is frozen — `business/sorella/profile.md`, `ada1d9e`, six sessions,
gated by `make check-profile`. What follows is the map, and the three small
things that have to be true before a map can be sealed.

---

- [ ] Sorella gets a store of its own, and Marlow's log is put back where it came from
      This has been true since the business changed and has never been an item.
      `business/` holds Marlow's `v1.yaml`, `draft.yaml`, transcripts, profile
      and questions. `seal`'s default `--into` is `business/`, and
      `resolve_version` globs `v*.yaml` in whatever directory it is pointed at,
      so Sorella's map sealed without thought lands as **v2 superseding a
      business that was retired on 2 Sep** — the failure of 28 Aug, returning
      because a directory was made for a profile and not for a store.
      The log is the other half. Its three tables carry no column that separates
      one business from another, so one log is one business by construction, and
      the working log still holds Marlow's 1 / 107 / 301. Clearing it costs
      nothing: the 29 Aug rule that the whole log must be reproducible from a
      source outside Postgres is satisfied by `business/draft.yaml`, which is
      committed, so re-sealing reproduces it exactly.
      done when: `business/sorella/` is the store Sorella's maps seal into and
      the command that does it is written down in `CLAUDE.md`; sealing Marlow's
      `business/draft.yaml` into an empty log reproduces 1 / 107 / 301 exactly,
      proving the clearing is reversible before it is done; the working log named
      by the default DSN is then empty at 0 / 0 / 0; `make check` still exits 0
      with its 64 tests; and nothing under `business/` outside
      `business/sorella/` is moved, renamed or deleted

- [ ] Sorella's competency questions are written and frozen
      `business/questions.md` is Marlow's, six questions, Q6 written to fail.
      Sorella has none. They are frozen before the map is drawn, because a
      question written after the map is a question the map can already answer —
      that is the 29 Aug rule and it is the one part of the author separation
      that survived 3 Sep, since the questions are the instrument and the profile
      is the material.
      The profile is frozen, so the material cannot move to suit them.
      done when: `business/sorella/questions.md` exists, holds between six and
      ten questions a person at Sorella would actually ask, each one answerable
      only from facts the profile states; at least one asks for a number that
      depends on a definition that changed after 15 June 2026; at least one asks
      a question about a day whose answer differs depending on when it is asked;
      at least one is expected to fail and says so and why; every question names
      the sections of the profile its answer comes from; and the session that
      writes it does not touch `business/sorella/profile.md`

- [ ] `make check` fails if the generator knows what a business is
      The claim milestone one rests on is that the graph carries the logic, and
      the failure that looks like success is a generator that carries it
      instead. Measured before writing the guard rather than after: every match
      for inventory vocabulary under `components/` today sits in a docstring, a
      comment or a usage example, and none in executable code — so the baseline
      is clean and the guard is worth having before the generator grows.
      `scripts/check_profile.py` is full of business vocabulary and is supposed
      to be; it is not under `components/` and the guard does not read it.
      done when: one script parses every `.py` under `components/` with `ast`,
      strips comments and docstrings, and reports any remaining occurrence of a
      business term drawn from a list it holds in one place; it exits 0 against
      the tree as it stands and non-zero when a term is planted into a live
      code path; `make check` runs it and the 64 tests that exist still pass

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
