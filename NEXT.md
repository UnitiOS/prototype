# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. This file had grown to
thirty finished items and two live ones, which is a log wearing a to-do list's
name.

The map stage is closed. `business/sorella/v1.yaml` — 21 classes, 101 slots,
4 aggregates, 2 nets, sealed `b8de674`, superseding nothing. Marlow's `v1.yaml`
is untouched. Four sittings: `a06de07`, `e3e012c`, `bf55836`, `b8de674`.
Four of v1's five gaps are answered and the fifth is answered with a refusal.
`§3.4`'s fifty-one rules and `§3.5`'s measures are deliberately outside this
map; adding them is a definition change and stage 7 has never had a real one.

What is left before milestone one is the 1 Sep onboarding order's second and
third steps: fill the master-data forms, then operate. Nothing has been
submitted — all 41 pickers over 12 classes offer nothing, and the log holds
101 URI registrations and no fact.

---

- [ ] Fill Sorella's master data through the generated forms
      Scoped by the day, not by the profile: **every entity entered must be
      named in `§4.1` or `§4.3`** — Monday 15 June's opening count and Tuesday
      16 June's movements. That is a checkable boundary, and it is what keeps
      this from becoming the eighty bought items and the thirty-one accounts.
      **Before entering anything, spend ten minutes on the thing that could
      make it worthless.** `resolve_version` returns `None` for every `as_of`
      before a map's `sealed_at`, and Sorella's v1 takes effect on 15 June and
      was sealed on 3 September — eighty days. `submit()` is unaffected because
      it takes the version off the file it was handed, but a reader asking what
      the map said on 16 June as known on 16 June gets nothing, and milestone
      one's whole week sits in that hole. Find out whether the balance can be
      computed at all before three hundred rows are typed into it, not after.
      **Say which way consumption goes.** `§3.2` has ingredients going to the
      machine as movements and `§2` has `RecipeLine` saying what a page eats.
      Whether Tuesday's consumption is recorded as movements the day states, or
      has to be derived from a batch and its recipe, decides whether recipes
      are master data this session needs at all. The profile answers it; this
      file does not.
      Two known defects are live and neither is to be worked around silently:
      the generator renders fillable forms for `IngredientOnHand` and
      `GelatoOnHand`, which are computed — do not submit to them; and the log
      cannot tell Marlow's 301 assertions from Sorella's by any column but the
      URIs a row names, so report Sorella's count separately rather than the
      table's total.
      done when: every entity submitted is listed in `LOG.md` against the
      `§4.1` or `§4.3` line that names it, and nothing is submitted that is not;
      `generate.py table` over the sealed map shows non-zero rows for each class
      filled and `--verify` is clean; `LOG.md` reports Sorella's assertion count
      apart from Marlow's 301 and states how it told them apart; `LOG.md` states
      whether `resolve_version` returns the map for an `as_of` in June and what
      was run to find out, before the bulk of the entry; `LOG.md` states whether
      Tuesday's consumption is recorded or derived, quoting the profile line
      that settles it; `make check` exits 0 with its 64 tests still passing;
      nothing under `business/` is added, moved, changed or deleted; and no
      value is submitted for any slot carrying an `aggregate` annotation or an
      `equals_expression`

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
