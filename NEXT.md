# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. This file had grown to
thirty finished items and two live ones, which is a log wearing a to-do list's
name.

The map is sealed — `business/sorella/v1.yaml`, `b8de674`, 21 classes, 101
slots, superseding nothing. The master data is in — `2787899`, 197 entities and
1,215 assertions through the generated forms, every one named in `§4.1` or
`§4.3`. Step three of the 1 Sep onboarding order is what is left: operate.

Two things found entering it, both recorded and neither yet acted on. The
balance computes off the sealed file at a June `valid_at` and lacks only
movements. And Tuesday's consumption is **derived, not recorded** — `§3.2` says
no document in this business records an ingredient leaving a shelf — so an
ingredient figure for Tuesday is `RecipeLine.line_quantity` scaled by
`batch_mix_quantity ÷ recipe_basis_quantity`, nothing in `components/` walks
that, and the twenty-two recipe pages are master data that is not yet entered.
Whether milestone one needs them depends on what `§4.3`'s evening count counts,
which is the next item's question and not this one's.

---

- [ ] The generator's row rule reads the class fact
      Entering the master data made every projection in the system worse, and
      the numbers are exact: yesterday ten tables held 0 rows and 41 pickers
      offered nothing; today all ten hold **197** and all 41 offer **197**. A
      unit is a row of the `BoughtItem` table and a supplier is a row of the
      `Flavour` table. The cause is one rule meeting one fact — a row is *the
      subject of at least one fact under one of this table's columns*, which
      the generator's own docstring admits is a guess, and `entity_class` is a
      column of fifteen of the twenty-one classes.
      The map already names the slot to read: `entity_class` carries
      `designates_type: true`, admitted on 2 Sep on the ground that it names
      which slot carries the type. Nothing has read it until now. Reading it
      stays domain-blind — the generator learns no business word.
      **One question this has to answer rather than assume.** `BoughtItem is_a
      Ingredient` and `Supplier is_a Location`. A class fact names one class, so
      a strict reading puts a bought item in no `Ingredient` table and a
      supplier in no `Location` table — and `movement_out_of` ranges over
      `Location`, so a strict picker would offer no supplier and Tuesday could
      not be entered. Whether the rule walks `is_a` is the decision inside the
      decision; settle it against what the forms need and say which way and why.
      This is a `components/generator/` change. It is not a repair: it changes
      what a projection is, from a guess to a read.
      done when: `generate.py table` over the sealed map, run for each of the
      ten filled classes, shows only entities whose class fact names that class
      — or names a subclass of it, if that is the way it went — and `LOG.md`
      carries the ten counts before and after; `--verify` is clean on all ten;
      `generate.py form` renders all 21 classes and `LOG.md` carries the picker
      counts for `movement_flavour`, `movement_out_of` and `movement_unit`
      before and after; no business word appears in any executable line of
      `components/generator/`; `make check` exits 0, and if tests were added
      `LOG.md` states the new total and what each new test would have caught;
      nothing under `business/` is added, moved, changed or deleted; and no
      assertion is written to the log by this session

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
