# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. This file had grown to
thirty finished items and two live ones, which is a log wearing a to-do list's
name.

---

- [ ] Sorella's profile, session 3: the rules, and how stock moves
      Session 2 landed at `d1a42f1` — 1,459 lines, 25 flavours with a page or a
      stated reason for having none, and the immutability check run here rather
      than read from LOG: sessions 3 and 4 are byte-identical to `9320fea` from
      the `# Session 3` heading to the end of the file. The file can now add and
      subtract. What it still cannot do is say what the business requires, or
      what anyone fills in.
      This session is where the 1 Sep reversal lands. The target artefacts are
      written before the graph is, and a document with no field list gives
      claim A nothing to fail against. It is also where the four rule shapes
      settled on 29 Aug get their material, and the annotation vocabulary may
      only grow against a rule the profile already states.
      §1.3 now names 38 places. The carried §6 was written when the file named
      five. Every place that nothing moves into or out of is a place the graph
      will carry and the log will never touch.
      done when: every place named in `§1.3` is named by at least one movement
      as a source or a destination; every movement states the document filled,
      who fills it, and the gap between the day it happens and the day it is
      written down, or states that there is none; every document named states
      every field on it in the order it is filled; every rule states its number
      and the date it last changed; the rules include at least one that sums
      over rows, one that is a ratio of two derived quantities, one that is a
      threshold producing an exception, and one that is a rate over a window
      feeding a threshold; the carried `§11` is re-examined item by item against
      sessions 1 and 2, each item either surviving with a reason or struck with
      one; the carried rules that sessions 1 and 2 made checkable are checked
      and every conflict stated, the free-delivery threshold against the four
      pan minimum and the credit-terms rule against the 31-account table among
      them; the file states no quantity on hand, no count and no event; it
      states no total, subtotal or derived figure; everything from the
      `# Session 4` heading to the end of the file is byte-identical to
      `d1a42f1`; every change to sessions 1 and 2 is a correction forced by a
      conflict and is listed in `LOG.md`; and `git show --stat HEAD` lists no
      file outside `business/sorella/profile.md`, `LOG.md` and `OPEN.md`

- [ ] `make check` fails if the generator knows what a business is
      The claim milestone one rests on is that the graph carries the logic, and
      the failure that looks like success is a generator that carries it
      instead. Measured before writing the guard rather than after: every match
      for inventory vocabulary under `components/` today sits in a docstring, a
      comment or a usage example, and none in executable code — so the baseline
      is clean and the guard is worth having before the generator grows.
      done when: one script parses every `.py` under `components/` with `ast`,
      strips comments and docstrings, and reports any remaining occurrence of a
      business term drawn from a list it holds in one place; it exits 0 against
      the tree as it stands and non-zero when a term is planted into a live
      code path; `make check` runs it and the 64 tests that exist still pass;
      and the working log named by the default DSN still reports 1 / 107 / 301

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
