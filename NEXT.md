# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

---

## The question this answers

**Does the screen show what is being claimed?** Item one built the business the
demonstration stands on and it works: eleven forms, two projections, 59 rows
that move when the clock moves, and a price whose own history executes. It also
looks like every generated CRUD screen ever built. Nothing a viewer sees says
the logic came out of a graph, that the log keeps what was wrong, or that a
number has a history.

This is demo item two, the surface. `ROADMAP.md` names all three.

Item one was validated on 7 Sep before this was written, and four small things
came out of it that belong here rather than in an item of their own.

---

## Open: the surface

### 0 · The four things validation found

None of them is mechanism, all four are visible.

- `demo-serve` binds a port of its own, **8100**. A `serve` from an earlier
  session held 8000 and answered with Sorella's `v3`, so the demonstration and
  the thing it replaced were both live and indistinguishable by URL.
- `render.py` tells the viewer the dropdown choices "were read out of the log".
  They come out of the operational store, and closing that read was a third of
  item one. The page currently contradicts the property it demonstrates.
- A blank `subject` returns 200 and writes nothing, while the field's own help
  text says one is minted. `submit()` mints it; the page then shows the URI it
  minted.
- A table at a clock before the seed renders "No rows at these clocks" and
  nothing else. It says the window instead: the log holds nothing before
  13 July 2026, and 16 June — the date milestone one names — is one of the
  clocks that falls outside it.

### 1 · The home page is a walk, not a menu

Six cards in order, named from the stages in `CLAUDE.md`: *what was said*,
*what it became*, *what was recorded*, *what was generated*, *live use*, and
*definition change*, the last dead and waiting on an item that does not exist
yet. One sentence and one link each.

The eleven forms and two tables that are the home page today become the
contents of the fourth card. A viewer arriving at `/` should be able to walk
forward without being told where to click.

### 2 · `/said` — the transcript beside the map

`draft.txt` as prose in the left column, `v1.yaml` in the right. A class or slot
on the right links to the sentence on the left that asked for it. Two stages on
one page: what a business said, and the map it became.

The transcript stands on its own already — item one wrote it that way — so this
renders a file, it does not author one.

### 3 · `/graph`, and the formula behind a column

Two views.

**The map.** Twelve classes and the relations between them. Sorella's twenty-one
were unreadable on a projector; twelve are not, which is a large part of why the
demo business is narrow.

**The formula.** From a column header in a table, a link to the piece of graph
that produced that column. `ingredient_stock_value` draws its expression, the
two aggregates it names, and the `parameter` annotation pointing at
`ingredient_pack_price` in the kernel. This is the one view that answers "how do
you know the logic is not in the code" without anybody having to take it on
trust.

Generated as Mermaid text from the map and rendered by one `<script>` from a
CDN. No build step, no framework, and no business name in any code path — the
node labels arrive from the map like everything else.

### 4 · `components/provenance/`, and a cell that opens itself

A new component, and the only thing outside the compiler that reads the kernel.
`CLAUDE.md`'s first property was amended for it the same day this item was
written; `DECISIONS.md` carries why.

One function: given a subject and a predicate, return every assertion ever made
about that pair — value, `valid_from`, `recorded_at`, `source`, `confidence`,
`authority`, `intent_id`, and what revokes what. No aggregation and no
judgement; it returns rows.

`/why?subject=…&predicate=…` renders them as a timeline, linked from a table
cell. The pistachio price is the one to demonstrate on: **two** rows standing
side by side, 203.00 valid from 13 July and 214.00 from 10 August, neither
revoking the other, and the table's own value column picking one according to
the clock the reader set.

The page is one door. The agent's MCP is the other, and it is item three, which
then holds transport rather than mechanism.

---

### Done when all seven hold

1. `make demo-serve` binds 8100, and `/` shows six stage cards rather than a
   list of forms.
2. `/said` shows the transcript and the map side by side, and clicking a class
   on the map side moves to the sentence that asked for it.
3. `/graph` draws the twelve classes, and the `ingredient_stock_value` column
   header links to a diagram naming both aggregates and the parameter.
4. `/table/IngredientOnHand?valid_at=2026-06-16` names the window it is outside
   of, rather than only saying there are no rows.
5. A form submitted with `subject` blank writes successfully, and the page shows
   the URI that was minted.
6. `/why` for the pistachio pack price shows **two** assertions with different
   `valid_from` and no `revokes` between them, and each carries its `source` and
   `authority`.
7. `make check` exits 0, and
   `grep -rn -i "gelato\|pistachio\|movement\|stock\|ingredient\|location" components/`
   finds no business term in a live code path.

### Not in this item

No MCP and no agent — item three. No shrinkage column. No fix to `happened_on`;
`OPEN.md` says why it is deferred. No authentication and no deployment. The
*definition change* card stays dead: sealing a `v2` of the demo map is a later
item and not this one. Anything found on the way is written into `LOG.md` as a
finding and left alone.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
