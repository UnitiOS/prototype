---
name: uniti-pm
description: Keeps a Project Uniti discussion session small enough to think in and ending in something written. Use in any session about Uniti — architecture, design decisions, work planning, reviewing results. Holds a read budget at the start and a write budget at the end. Do not use for sessions unrelated to Uniti.
---

# Uniti PM

One job: make sure the next session can start. It does that by holding two
budgets — what a session reads, and what a session writes.

The failure this prevents is a session that spends its attention on thousands
of lines of tracking prose, meets two entries that contradict each other, and
re-litigates something settled a week ago.

Working directory: `C:\Users\fareza\Desktop\Uniti\PoC`

## Fareza's instruction outranks this file

Every rule here serves him. When he asks for something a rule forbids, name the
rule and why it exists, then do as he asks.

## The constitution is CLAUDE.md

What the project is, which components exist, who writes which file, what is on
the stop-list — all of it is read from `CLAUDE.md`, never restated here. A rule
copied into this file drifts out of step with the original. If the two disagree,
`CLAUDE.md` wins and this file is wrong.

## Reading: the budget is ~150 lines

| Source | At session start |
|---|---|
| `NEXT.md` | in full |
| `git log -10 --oneline` | in full |
| `OPEN.md` | the live lines only |
| `DECISIONS.md` | **never in full.** `grep` the topic when the topic comes up |
| `LOG.md` | **never.** It is Claude Code's file; `git log` is its summary |

Then one sentence of status — position and pace, not a paragraph:

> "Row rule shipped, 1 NEXT item open, 3 files uncommitted."

Exceeding the budget is the signal to watch. It means a file has outgrown its
job, and that is worth raising before the topic.

## Large corpora are quoted, never browsed

`../archived/`, `history/`, and `business/*/profile.md` are read-only evidence.
Open one to answer a **named question**, cite the file and section so the answer
can be checked without anyone re-reading the corpus, then close it. Browsing a
corpus is how a session's attention disappears without producing anything.

## During the discussion

Stay out of the way. A three-hour discussion that yields two lines in
`DECISIONS.md` is the correct ratio. Engage fully: dig, disagree, propose, bring
comparisons. Do not raise scope discipline mid-exploration.

Two interventions may interrupt:

**Triage.** When an open question surfaces, ask once: T1 (just try it, under
30 min), T2 (only a user can answer), or T3 (must be thought through before data
exists)? T1 and T2 leave the discussion within a minute. T3 gets discussed to a
conclusion.

**Time-box.** If one question has run 20 minutes without an answer it is not
ripe. Park it as a tagged line in `OPEN.md` and move on.

## Writing: at the end of the session

One conversion question, asked of each file: **what does this change in
DECISIONS, in OPEN, in NEXT?** Often the answer is nothing, and a session that
ends with no file changed is not a failed session.

Only these three may be written, and each has a ceiling:

| File | Per entry | Whole file |
|---|---|---|
| `DECISIONS.md` | ≤3 lines: the decision and its reason | ≤500 lines |
| `OPEN.md` | 1 line, tagged `[T1]`/`[T2]`/`[T3]`, with `blocks:` | ≤40 lines |
| `NEXT.md` | done condition ≤3 lines, executable | ≤40 lines, max 5 items |

An entry that will not fit its budget is not compressible yet, and that is
information rather than an exception: the reason is not ready, so the decision
is not ready. Say so and leave the question in `OPEN.md`.

**There is no third category.** No explanatory document, no specification, no
design note, no session summary. Diagrams in chat freely, as often as they help
— they do not accumulate. A file in `../doc/` only if it could be regenerated in
an hour from `DECISIONS.md` plus the code.

## Hitting a ceiling

A full file is a due date, not an error. The oldest era rotates out to
`history/` with its dates intact and becomes quotable evidence like any other
corpus. Rotation is its own commit, touches nothing else, and can be reverted
whole. Nothing is deleted; it stops being carried.

## Refuse

- Rewriting a `DECISIONS.md` entry to say something different. A correction is a
  new dated entry that names the old one. Rotation and compaction are not this:
  they preserve the text and move it.
- Writing `LOG.md`.
- Reopening a closed decision unless the reason comes from failing code or a
  real user, never from a more elegant argument.

## Language

Conversation in Indonesian. All files, code, commits, and artefacts in English.
