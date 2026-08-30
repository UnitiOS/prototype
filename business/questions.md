# Marlow Gelato — competency questions

Frozen before any history is curated. Written from the five classes named in the
27 Aug decision and from `business/profile.md`, before the map exists and before
a single act is written. Data curated first would be curated to answer whatever
questions its author imagined, and the demo would then validate itself.

Each question is written the way Marta would say it, not the way a system would
ask it. A question nobody would utter is not evidence that the system is useful.

Q6 is expected to fail. A set of questions that all pass was, by construction,
never a test. If Q6 turns out to have a good answer, that is a finding; if it is
quietly dropped, the whole exercise is a performance.

---

## Q1 — what we believed on a past date

> "The March report I gave the bank — if I open it again now, it should still
> say the same thing. Which one is right?"

Class: what we believed at a past date, with the knowledge of that date.
Needs from the data: a recorded month-end close for March, and at least one fact
about March that was only learned after March closed.

## Q2 — the same report under two definitions

> "Shrinkage was three percent in March and eight in July. Am I wasting more, or
> did the way we count it change?"

Class: the same report under the old and current definition.
Needs from the data: two map versions whose shrinkage definition genuinely
differs, sealed at two different instants.

## Q3 — why the number moved

> "Last month the March report said one thing, now it says another. Was
> something recorded late, was something wrong and fixed, or did I change how
> it's counted?"

Class: whether a number moved because of data, a correction, or a definition.
Needs from the data: one metric, one period, moving for all three reasons.

## Q4 — what is still not known

> "How much can I trust this raw material number? What was actually counted,
> what's a guess, and what have I never recorded at all?"

Class: what is still not known about something.
Needs from the data: `confidence` actually used — no writer has ever set it —
a slot in the map that never receives a fact, and a predicate left orphaned
after v2.

## Q5 — recorded facts against stated rules

> "I said stock can't go negative and anything under five litres gets made
> again. When did my own records break that this year?"

Class: whether what was recorded is consistent with the rules that were stated.
Needs from the data: the threshold rules from profile §10 in the map, and
recorded facts that violate them.

## Q6 — the disputed number (expected to fail)

> "Two people counted the same freezer that day and got different numbers. Both
> of them are honest. Which one does this thing keep?"

Class: none of the five — this is the one we expect to break.
Why it should fail: the read rule breaks a tie on record time and returns one
answer, so the dispute disappears. That is the same failure as an ERP
overwriting a value, which is the thing this system claims not to do.
Needs from the data: two counts of the same subject at the same `valid_at`,
recorded at different instants, neither revoking the other.

---

Written 2026-08-30, before `business/draft.yaml` exists. Not revised afterwards.
If a question turns out to be unanswerable, that is recorded as a finding in
`LOG.md`, not fixed by rewriting the question.
