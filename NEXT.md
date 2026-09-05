# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.
A done condition is three lines. Longer means the item has become a
specification, and a specification decides things the work has not reached yet.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file.

The design was frozen on 5 Sep — `CLAUDE.md`, "The three layers" and "Where a
rule lives". No rule in the graph executes until the compiler exists.

The map is sealed — `business/sorella/v1.yaml`, `b8de674`, 21 classes, 101
slots. Master data is in: 197 entities, 1,215 assertions. The log holds no
`StockMovement`, so there is no balance to compute yet.

---

- [ ] Movements in the log, enough to compute one balance by hand
      `IngredientOnHand` declares aggregates over `StockMovement` and the log
      holds none. The aggregate does not group by unit, so the seed is one
      ingredient in one unit — mixing units would sum 2 kg and 500 g into 2.5
      and the test would measure nothing. Movements from profile §4.1 and §4.2.
      done when: the seed submits through `generate.py submit`; `generate.py
      table business/sorella/v1.yaml StockMovement` lists them; `LOG.md`
      carries the hand-computed net for that ingredient at each location

- [ ] The compiler makes one declared rule execute
      The map carries four `aggregate` annotations and two `equals_expression`;
      `grep` finds zero of them in `generate.py`. Read them instead: emit
      `CREATE TABLE p_<class>` from `columns()`, fill aggregate columns by
      grouping the `over` class per the `by` map, then evaluate the expression.
      done when: `make compile` fills `p_ingredient_on_hand`; its net equals the
      hand computation in `LOG.md`; grep for `stock|ingredient|gelato|movement|
      quantity` over `components/compiler/` returns nothing

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
