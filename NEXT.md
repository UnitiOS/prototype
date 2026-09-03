# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. This file had grown to
thirty finished items and two live ones, which is a log wearing a to-do list's
name.

The profile is frozen — `business/sorella/profile.md`, `ada1d9e`, six sessions,
gated by `make check-profile`.

Session 1 is done — `a06de07`, 11 classes, 38 slots, `§1.1` to `§1.9`.
Session 2 is done — `e3e012c`, 3 classes and 20 slots added, `§2.1` to `§2.7`.
Session 3 is done — `bf55836`, 7 classes and 41 slots added, `§3.2` and `§3.3`,
and 4 aggregates. It was to have left a map milestone one could run on and did
not, for one reason: this file forbade `equals_expression`, so the balance
ships with `in` and `out` and no net. That was a constraint written here, not
something discovered, and the third column is one slot.

`§3.4`'s fifty-one rules and `§3.5`'s contested measures are **not in this
map**, and that is now deliberate. Nothing in them touches arrivals minus
departures, so milestone one does not need them — and adding them later is a
definition change, which is stage 7, which has never had a real change to
replay. Sealing before them gives it one.

---

- [ ] Close the map: the net column, the seal, and the first generated forms
      Four steps in order, and the last one is the point.
      **One.** A net on each balance class — `ingredient_on_hand_net` and
      `gelato_on_hand_net`, each an `equals_expression` over the two aggregates
      that are already there. Session 3 measured what it returns rather than
      assuming: `'{a_in} - {a_out}'` over 0 and 5 gives `Decimal('-5')`, not a
      string and not an error. `equals_expression` is permitted from here.
      **Two.** The provenance note `annotations.transcript` has to name. `seal`
      requires the annotation and requires the file it names to exist, and the
      draft has carried only `valid_from` since session 1. It goes in
      `business/sorella/`.
      **Three.** The seal, once, with `--into business/sorella/`. The default is
      `business/`, which still holds Marlow's retired v1 — sealing there lands
      Sorella as a v2 superseding a business retired on 2 Sep, which is the
      28 Aug failure repeating. If `seal` refuses the draft, the refusal is the
      result and is reported rather than worked around.
      **Four.** The generator, pointed at the sealed map, and the forms it
      renders held against v1's gaps. That list was written on 1 Sep, before
      Sorella existed, so it cannot have been tuned to the map that answers it:
      no supplier was nameable, nothing consumed anything so material stock
      could only rise, no pan was minted so `PanMoved` and `PanPulled` were
      forms about a thing that did not exist, there was no opening stock and no
      price and no adoption date, and four movement classes rendered
      byte-identical forms.
      One trap in reading that comparison, and it decides whether the answer
      means anything: **an empty dropdown is not v1's failure repeating.**
      Master data enters through forms under the 1 Sep line, so a freshly sealed
      map has no supplier rows yet and a picker over `Supplier` will be empty.
      v1's defect was that no class existed to pick over at all. The question is
      whether the form offers a picker over a class that exists and can be
      filled, not whether anything is in it today.
      done when: the net slot exists on both balance classes and `gen-owl` over
      the draft exits 0; `business/sorella/` holds a sealed version file and the
      transcript its annotation names; `seal` was run once with
      `--into business/sorella/` and nothing under `business/` outside
      `business/sorella/` was added, moved or deleted; the generator was run
      against the sealed map and `LOG.md` carries what it rendered, or carries
      the refusal and what caused it; `LOG.md` answers each of v1's five gaps
      with a yes or a no and the evidence for it; `make check` exits 0 with its
      64 tests still passing; and `business/sorella/profile.md` is unchanged

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
