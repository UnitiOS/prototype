---
name: uniti-interview
description: Run a Uniti interview — someone describes their business in ordinary conversation, and the description becomes a LinkML draft that `seal` turns into a map version. Use when interviewing anyone about their business for Uniti, or resuming an interview from an existing draft. Do not use for sessions about Uniti's own architecture.
---

# Uniti interview

The session produces two files and nothing else:

- `business/draft.yaml` — the map, and every stated fact in its annotations
- `business/draft.txt` — the transcript. Evidence, not a fact

Working directory: `C:\Users\fareza\Desktop\Uniti\PoC`

Nothing reaches the kernel until the person asks to seal.

## A conversation, not a questionnaire

There is no script here on purpose. Ask about the business the way anyone
curious would, follow what is interesting, and let the mapping be your problem
rather than theirs.

The person never learns a word of ontology vocabulary. Not class, not slot, not
predicate, not entity. If a sentence you are about to send contains one, it is
the wrong sentence. Ask "is that the same thing as the tubs out front, or a
different thing?" — never "is that a subclass?".

Follow-ups are the method. A statement that arrives whole is usually
underspecified: what someone calls one thing is often two, and what they call
two things is often one. Ask again rather than deciding quietly.

## The draft is the session

The conversation will run past the context window. The draft will not.

Before every addition: re-read `business/draft.yaml` from disk, revise it whole,
write it back whole. Never append blindly, never trust your memory of what is in
it. This is also what lets a statement at minute 60 correct one from minute 10,
and what lets the session resume in a fresh window.

If a draft already exists when the session starts, read it first and say what it
already covers before asking anything new.

Keep `business/draft.txt` current as the session goes. A transcript
reconstructed at the end is a summary, and a summary is not evidence.

If a `draft.txt` is already there when the session opens, it belongs to an
earlier conversation. Overwrite it before writing a line of your own. `seal`
copies the transcript rather than moving it, so a leftover file will be sealed
beside a version it has nothing to do with, and nothing will complain.

## What `seal` refuses

A refused draft wastes the session. Every one of these is enforced in code:

- **Every top-level slot declares an explicit `slot_uri`.** No exceptions. The
  URI is the slot's identity in the log and it survives renames — when the
  person changes what they call something, change the slot name and leave the
  `slot_uri` exactly where it was.
- **`annotations.valid_from` is required**, never guessed. It is the date this
  description takes effect in the business. Ask for it. Do not infer it from
  today, and do not reach for an unbounded past.
- **A fact is exactly three keys** — `subject`, `predicate`, `value`. Never a
  fourth. `predicate` must be a `slot_uri` this draft declares, and `value` is
  one scalar.
- **`annotations.transcript` names the transcript file**, relative to the draft:
  `transcript: draft.txt`. The file must exist when you seal. A conversation
  that was not saved cannot be recovered, so this is refused rather than
  warned about. `seal` copies it beside the version it belongs to, as
  `vN.txt`, and rewrites the annotation to name the copy. The draft's own
  transcript is left where the session left it.
- **The top-level `annotations` block is flat**, except for `facts`. Every other
  annotation carried into a sealed version must be a scalar. The version
  resolver reads that block with a shallow scanner: a mapping nested under it
  leaks its keys upward, and a nested `valid_from`, `sealed_at`, `supersedes` or
  `transcript` silently overwrites the real one — wrong version resolved, no
  error. Note which shape this catches: `value` plus a nested `annotations` is
  what LinkML's own documentation teaches, so the correct-looking thing is the
  dangerous one. Slot-level annotations are untouched by any of this.
- The draft must load as LinkML.

## One trap that is not enforced

**Facts are stripped when the draft is sealed.** After a seal they live in the
log, not in the file. The sealed version is not a place to look them up.

## Rules the person states

People state rules constantly — what counts as shrinkage, when stock is low, how
a tub becomes a sale. The shape a rule takes in the map is not decided yet, and
deciding it from a guess is the thing this stage exists to avoid.

So record the rule, not a formalisation of it. Attach it to the slot it is
about, in the person's own words:

    slots:
      shrinkage:
        slot_uri: uniti:shrinkage
        annotations:
          stated_rule: what we counted minus what the book says, per flavour,
            end of the month

Verbatim beats tidy. The rules collected here decide what the generator becomes;
a rule cleaned up into pseudo-SQL has already made that decision.

## Before sealing

Read the map back in business language — what you understood, as sentences about
their shop, in their words. Not a diagram, not a list of classes. Someone who has
just described their business cannot judge boxes and arrows; the graph render
exists for the team measuring blast radius, not for them.

Correct whatever they correct, in the draft, before going further.

## Sealing

Only when they ask for it.

    .venv/Scripts/python.exe components/seal/seal.py business/draft.yaml --actor <name>

Exit 0 means a new `business/vN.yaml` exists and every stated fact is in the log
under one intent. A non-zero exit means nothing was written anywhere — read the
message, fix the draft, run it again.

**If this session is a dated episode, say so.** A role-played business is
described across several sittings standing for several months, and the report
that comes later needs those sittings to have been recorded at different
instants. Without `--sealed-at` the seal is stamped today, every episode lands
at the same moment, and the spread the report depends on never exists — with
nothing to warn you.

    ... --actor <name> --sealed-at 2026-01-15T09:00:00Z

Ask which instant this sitting stands for. It is the same question as
`valid_from` and it has a different answer: `valid_from` is when the description
takes effect in the business, `--sealed-at` is when the describing happened.

## A second interview about the same business

One question a first interview cannot ask: **since when?** A definition that
changes needs the date it changed, or `valid_from` has no honest answer and
`seal` refuses the draft. That single question is the only thing that makes a
later interview different from a first one.

Start from the newest sealed version rather than a blank draft: copy it to
`business/draft.yaml`, drop the `version` key and the `sealed_at` and
`supersedes` annotations, and set the new `valid_from`.

## What a good session produced

Not a large map. A findable one.

The test that matters comes later: when one definition moves, how much of the map
moves with it. If moving shrinkage touches one place, the session went well. If
it touches a class hierarchy, three rules and a projection, the same fact was
written in several places — which is a finding worth having, not a mess to tidy
away before anyone sees it.
