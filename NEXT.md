# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

---

## The question this answers

**Is there enough world in the log to make the substrate visible?** Item one
built the business, item two built the surface, and both passed every condition
they were given. Validation on 7 Sep found what neither item asked about.

The whole demo log was recorded in **one second** — `recorded_at` runs from
`2026-09-06 23:08:59` to `2026-09-06 23:08:59` — and holds **no `revokes` at
all**. So `as_of` is a cliff and not an axis: nothing, nothing, nothing, then
everything. And a correction, which `CLAUDE.md`'s first settled finding calls
*the product* and holds apart from a change, has no data anywhere to be shown
with.

This is the first basket, **missing information**. `perform.py` already takes
`recorded_at` as an argument and `resolve.py` already names the backfilled case
in its own docstring. The mechanism is there and the seed did not use it.
Nothing has been learned about the system, and nothing is being widened here.

This item goes between the surface and the agent, because the agent's strongest
demonstration is a correction that withdraws rather than overwrites, and there
is nothing in the log for it to withdraw.

---

## Open: the data, and a table that can be read

### 1 · A seed with both clocks alive

`recorded_at` is stated per assertion rather than left to default. Facts arrive
late the way §3.2 of the profile records them arriving late, in its own *lag*
column: a delivery note reaches the office tray three days after the morning it
is dated, a text message the same evening, a till receipt a fortnight later. The
two clocks then say different things, which is the entire point of there being
two.

And **corrections**, which the log has never held one of: a count line written
wrong and put right, a price mistyped and withdrawn, a delivery recorded that
turns out never to have arrived. Each is an assertion carrying `revokes`, and a
pure retraction carries no value at all.

A correction is not a change. Both must be in the seed and they must be
distinguishable, because telling them apart is the claim.

### 2 · Volume

| | now | after |
|---|---|---|
| ingredients | 8 | about 20 |
| movements | 190 | 800–1,000 |
| count sheets | 2 | about 6 |
| `valid_from` window | 6 weeks | 6 months |
| distinct `recorded_at` days | 1 | 20 or more |
| assertions carrying `revokes` | 0 | 30 or more |

The seed stays deterministic: run twice from empty, the same counts both times,
as item one's did.

### 3 · Provenance with something in it

`source`, `confidence` and `authority` vary and have reasons. A note signed at
the door is not held with the confidence of a number remembered a week later,
and §3.2's *document* and *lag* columns already say which is which for every way
stock moves. Nothing is invented; the profile is read.

Today `confidence` is null on all 2,237 rows and `authority` has two non-null
values, so the columns that make this substrate different from a table render
empty on screen.

### 4 · Names, not URIs

A projection cell shows `sorella:item_base_50_stabiliser` and a column header
shows `ingredient_where`, while a form beside it shows "Dry store" and did so
already.

Both are repaired in the map plus one rendering rule. The map declares five
identifier slots — `item_name`, `location_name`, `unit_name`, `person_name`,
`kind_name` — and the renderer resolves a ref cell through the identifier of the
class the slot ranges over, out of the operational store. None of its 51 slots
carries a `title`; they get one, and a column header prints it.

No branch on any business word, and **no `slot_uri` moves**. What the business
calls a thing changes in the map; what the thing is stays where it was. That is
`CLAUDE.md`'s claim about slot identity, made visible rather than asserted.

### 5 · A table that can be used

Sort by a column, filter by ingredient and by place, and a clock control that
can be moved rather than an ISO timestamp that has to be typed. The volume above
is what makes this necessary; at 59 rows it was merely missing.

Server-rendered where it can be. No framework and no build step.

---

### Done when all six hold

1. `make demo-seed` from empty gives **20 or more ingredients**, **800 or more
   movements**, a `valid_from` span of **six months or more**,
   `count(DISTINCT recorded_at::date) >= 20`, and
   `count(*) WHERE revokes IS NOT NULL >= 30`. Run twice from empty, the same
   counts both times.
2. `/table/IngredientOnHand` at one `valid_at` and three different `as_of`
   values returns **three different results** — not nothing, nothing, nothing,
   then everything. The three are written into `LOG.md`.
3. `/why` for at least one subject and predicate shows a **revoked** row, marked
   as revoked, beside the row that revoked it and the intent that carried it.
4. No `sorella:` appears in any ref cell of `/table/IngredientOnHand`, and every
   column header reads as words rather than as a slot name.
5. Sorting a column reorders the rows; filtering to one ingredient reduces the
   row count; the clock is moved without typing an ISO timestamp.
6. `make check` exits 0, and
   `grep -rn -i "gelato\|pistachio\|movement\|stock\|ingredient\|location" components/`
   finds no business term in a live code path.

### Not in this item

No MCP and no agent — item three, which this one unblocks. No shrinkage column.
No framework and no build step. No fix to `happened_on`; `OPEN.md` says why it
is deferred. The *definition change* card stays dead.

The targets in condition 1 are proposals and may be argued down, with one
exception: a spread `recorded_at` and thirty corrections are the reason this item
exists, and lowering those two removes the item rather than shortening it.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
