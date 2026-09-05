---
name: uniti-discuss
description: Discussion mode for Project Uniti — architecture, design questions, reviewing a result, choosing what to work on next. Use when the session is about deciding something rather than building it, and when a conclusion should end up in DECISIONS.md, OPEN.md or NEXT.md. Do not use for running an item from NEXT.md; that is uniti-build.
---

# Uniti — discussion

The job is to think with Fareza and leave the next session able to start.

`CLAUDE.md` is what the system is, and nothing here restates it. If the two
ever disagree, `CLAUDE.md` is right and this file is wrong.

## Getting oriented

Four things, in this order, and each answers a different question:

| Read | To learn |
|---|---|
| `ROADMAP.md` | which milestone, which stages have run, which components exist |
| `NEXT.md` | what is being worked on, and its done condition |
| `OPEN.md` | what is unresolved, and what is known-broken and left alone |
| `git log --oneline -10` | what actually happened lately |

`LOG.md` is the detail behind the last few commits — read the entry for a run
being discussed, not the file. `DECISIONS.md` is walked by `grep` for the topic
in hand; its standing-rules index at the top says which entry governs a topic
today, and the dated entry below wins where the two disagree.

`../archived/`, `history/` and `business/*/profile.md` are evidence, not
context. Open one to answer a named question, cite the file and section, then
close it.

Then say where things stand in a sentence or two before the topic starts.

## During

Engage properly. Dig, disagree, propose, bring comparisons, sketch diagrams in
chat as often as they help. A three-hour discussion that yields two lines in
`DECISIONS.md` is the correct ratio, and a session that changes no file is not
a failed session.

Two things are worth doing as they come up rather than at the end:

**Type an open question when it surfaces.** `OPEN.md` defines `[T1]`, `[T2]`
and `[T3]`. A T1 is answerable by trying it — say so and offer to try it rather
than debating it. A T2 needs a real user and is out of scope for the PoC. A T3
is the kind worth the discussion.

**Say when a question is not ripe.** A question that has been turned over
without converging usually lacks something — a result that has not been run, a
number nobody has. Name what is missing, park the question as a line in
`OPEN.md`, and move on.

## Where a conclusion lands

One question, asked of each thing concluded: what does this change in
`DECISIONS.md`, `OPEN.md`, or `NEXT.md`? Often nothing, and that is a real
answer.

| File | What goes in |
|---|---|
| `DECISIONS.md` | a decision and its reason, dated, appended. Never an edit to an existing entry — a reversal is a new entry naming what it reverses |
| `OPEN.md` | a question, one line, typed, with `blocks:` naming a stage or component. Answered lines leave; the answer's home is `DECISIONS.md` |
| `NEXT.md` | an item with a done condition that can be run as a command |

`NEXT.md` and `DECISIONS.md` are written **after Fareza has agreed to the
wording**, not from an inference that he would agree. Propose the exact line and
wait.

A conclusion that resists being written short is usually not finished. That is
information rather than a formatting problem: the reason is not ready, so the
decision is not ready. Say so and leave the question in `OPEN.md`.

The file set is the seven in `CLAUDE.md`. A conclusion lands in one of them
rather than in a new specification, design note or session summary.

## Reopening

A settled finding in `CLAUDE.md` reopens on failing code or on a real user. It
does not reopen on a more elegant argument, and an elegant architecture idea
arriving mid-stream is recorded in `OPEN.md` rather than built.

## Language

Conversation follows Fareza. Everything written to disk is English.
