# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

---

## The question this answers

**Is there something a person can be shown?** The loop runs in a browser and
that was the last item's answer to "is there anything a person can use". This
one is different: nineteen forms and two tables is a menu, not a story, and a
form over a table looks like every generated CRUD screen ever built. Nothing on
screen shows what is actually being claimed.

The demo lap fixes that in three items and `ROADMAP.md` names all three. **This
is item one, and it builds none of the surface and none of the agent.** It
builds the business they will stand on: a narrow map, two stores of its own, and
a seed large enough that the tables look like a working system rather than a
fixture.

---

## Open: the demo business

### 1 · `business/sorella_demo/` — the map, narrow

Authored by hand and sealed through `seal`, exactly as Sorella's was. The
interview stage stays deferred (`DECISIONS.md`, 29 Aug).

Eleven classes, drawn from Sorella's twenty-one and carrying the same
`slot_uri`s wherever a slot means the same thing — a slot's identity is its URI
and renaming the business must not mint new ones:

| Class | Why it is here |
|---|---|
| `Ingredient` | the things counted |
| `Unit` | what they are counted in |
| `Location`, `InternalLocation`, `Supplier` | both ends of a movement; direction falls out of them |
| `MovementKind` | which of the ways stock moves this was |
| `Person` | who wrote it down |
| `StockMovement` | the delivery note and the waste sheet, one class |
| `StockCount`, `StockCountLine` | the count sheet |
| `IngredientOnHand` | arrivals, departures, net, and value from a kernel parameter |
| `CountedOnHand` | what the count sheets found, aggregated the same way |

`CountedOnHand` is new to this map: an `aggregate` over `StockCountLine` by
ingredient and place. Whether the two can be subtracted in one expression across
two classes is **not this item's question** — the two tables stand side by side
and a reader takes the difference. If it turns out the compiler already does it,
that is a `[T1]` to try in thirty minutes, not a thing to build here.

**The transcript, `draft.txt`, stands on its own.** It is not a pointer into
`profile.md` and not a fabricated chat log — a faked interview would be
`CLAUDE.md`'s third basket, passing by cheating. It is the business described in
prose, readable by somebody who has never opened this repository, and long
enough that every class and every slot in the map has a sentence somewhere that
asks for it. Item two puts it on screen beside the map it became.

### 2 · Two stores, and a seed that fills them

| Database | What |
|---|---|
| `uniti_demo` | the kernel. Its own log, so nothing here touches `uniti`, `uniti_trial` or `uniti_check` |
| `uniti_demo_ops` | the operational store. Derived, dropped and rebuilt |

`scripts/seed_demo.py`, and **every write goes through `generate.submit`** —
one `intent` and N `assertion` per action. A direct `INSERT` would make the one
write gate a fiction on the very data the demonstration is about.

What it seeds, sized so the tables read as real:

- 6–8 ingredients under their real names from `profile.md` §1.6
- 2 internal locations and 3 suppliers, and the units they are counted in
- the movement kinds the three documents use
- **6–8 weeks of movements, roughly 200**, ending before today, so that moving
  `valid_at` backwards changes both the row count and the numbers
- 2 count sheets inside that window

Dated in the past on purpose: a write through the form lands at now, later than
every seeded row, so the loop still moves a balance and the clock still rewinds.
A backdated entry is the one thing that cannot be shown, and `OPEN.md` carries
why.

### 3 · Four projections for the ref fields

`generate._options` reads `assertion` to fill a dropdown, which is the read path
`CLAUDE.md` forbids; it was knowingly left open on 6 Sep because closing it
needed a projection for every class a ref field ranges over and only two classes
had one. This map ranges its ref fields over four — `Ingredient`, `Unit`,
`Location` and `MovementKind` — so each gets a projection and `_options` reads
the operational store instead.

Additive: `generate._options` gains a path, it does not lose one. Sorella's map
still resolves the old way where no projection exists.

### 4 · `make demo-seed` and `make demo-serve`

    DEMO_DB     := uniti_demo
    DEMO_OPS_DB := uniti_demo_ops

Built on the pattern `serve` already uses: bring the container up, create the
database if it is absent, then run. `MAP` is `business/sorella_demo/v1.yaml`.

---

### Done when all six hold

1. `seal` produces `business/sorella_demo/v1.yaml` from the draft, and
   `make demo-seed` fills `uniti_demo` from empty. Rerunning `demo-seed` from
   empty produces the same assertion count.
2. `make demo-serve`, then `http://localhost:8000/` lists the **three document
   forms** — `StockMovement`, `StockCount`, `StockCountLine` — grouped apart
   from master data, and **two tables**.
3. `/table/IngredientOnHand` shows **more than 50 rows**, and moving `valid_at`
   back four weeks changes both the row count and at least one balance. The
   numbers at the two clocks are written into `LOG.md`.
4. Every dropdown on the three forms is filled with names, and
   `grep -n "assertion" components/generator/generate.py` shows `_options`
   reaching the operational store for the four projected classes.
5. **The loop.** A movement submitted through the browser adds one `intent` and
   N `assertion` to `uniti_demo`; reloading `/table/IngredientOnHand` at the
   default clocks shows the balance moved. No script runs between the two.
6. `make check` exits 0, and
   `grep -rn -i "gelato\|pistachio\|movement\|stock\|ingredient\|location" components/`
   finds no business term in a live code path.

### Not in this item

No navigation redesign, no graph view, no transcript page, no provenance
drill-down — that is demo item two. No MCP and no agent — item three. No
shrinkage column. No fix to `happened_on`. Anything found on the way is written
into `LOG.md` as a finding and left alone.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
