# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. This file had grown to
thirty finished items and two live ones, which is a log wearing a to-do list's
name.

The profile is frozen — `business/sorella/profile.md`, `ada1d9e`, six sessions,
gated by `make check-profile`. The map is drawn from it across four sessions,
one item in this file at a time, ordered so that stopping after the third still
leaves a map milestone one can use. Nothing is sealed until the last of them.

Session 1 is done — `a06de07`, 11 classes, 38 slots, `§1.1` to `§1.9`.
Session 2 is done — `e3e012c`, 3 classes and 20 slots added, `§2.1` to `§2.7`.

---

- [ ] Map session 3 of 4 — every way stock moves, and the eighteen documents
      `§3.2` and `§3.3`. This is the session that has to leave a map milestone
      one can run on, so it carries the balance as well as the movements.
      **Two things have to come out of it, and the first is inherited.**
      Session 2 ended by raising that gelato in a pan is not a thing the map can
      name: a batch makes gelato of a flavour, the gelato fills pans, tubs and
      minis, the pans sit in the holding freezer for up to 21 days, and the map
      has `Flavour` for the cabinet card and `SoldProduct` for the price line
      and nothing that is "pistachio in a 5 L napoli pan". A movement's quantity
      is of something, and that something has no name yet. Milestone one's
      closing balance runs straight through it.
      **The second is the balance itself.** Stock on hand is arrivals minus
      departures, which is arithmetic across rows, which the 1 Sep line puts in
      the aggregate annotation and the 2 Sep line shapes as one annotation whose
      tag names the computation and whose `value:` carries `over`, `sum` and
      `by`. Whether that shape can carry a sign — a movement subtracts at its
      origin and adds at its destination, and it is one row — is not known, and
      finding out is the session's job rather than something to work around.
      **`§3.3` is where the 1 Sep reversal gets executed.** The eighteen
      documents are the target artefacts the reversal asked for, and they were
      written as a description of the business rather than designed against a
      map, so they cannot be tuned to the map that answers them. The session
      says of each one whether the map can produce it.
      Vocabulary widens by one: **aggregate annotations**. Still forbidden:
      facts, `any_of`, LinkML class `rules`, `equals_expression`.
      v1's failures here are on record and none of them is to be repeated: four
      movement classes that rendered byte-identical forms, location folded into
      pan slot names, and nothing anywhere saying that goods received add and
      waste subtracts. The first is answered by the 1 Sep rule that a class
      earns its existence by changing the shape of its form; the third by the
      1 Sep rule that the outside of the business is locations, so direction
      falls out of an origin and a destination instead of being declared.
      done when: `business/sorella/draft.yaml` is the only file changed besides
      `LOG.md`; it still holds no `annotations.facts` block; sessions 1 and 2's
      14 classes and 58 slots are all still present, and any renamed, re-ranged
      or re-homed are listed in `LOG.md` with the reason; with
      `PYTHONIOENCODING=utf-8` set, `gen-owl` over it exits 0 and
      `gen-mermaid-class-diagram -d` into a directory outside the repo exits 0;
      searching it for `any_of` finds nothing; `make check` exits 0 with its 64
      tests still passing; `business/sorella/profile.md` is unchanged; nothing
      under `business/` outside `business/sorella/` is added, moved or deleted;
      and `LOG.md` names every `§3.2` and `§3.3` subsection consumed and every
      one left with the reason, carries the mermaid render of the classes this
      session added or changed and no others, states in one paragraph what a
      movement's quantity is of and whether the map can now name gelato in a
      pan, and lists all eighteen of `§3.3`'s documents with a yes or a no
      against each for whether the map can produce it

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
