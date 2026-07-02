# Entity page template

Use this shape when stubbing a new `<Domain>/wiki/people/<name-slug>.md`.
**This template is the canonical shape, follow the sections below.** A profile
holds durable facts; meeting chronology lives in the graph (backlinks +
`index.md`), not on the page. Do not build append-style "Past Discussions"
recap logs.

## Frontmatter

```yaml
---
type: person
description: "<First Last> (<role>), one-line context: who they are to the user."
aliases:
  - <firstname-lowercase>
  - <Firstname>
  - <First Last>
  - <any other names they go by: nicknames, handles, email-username>
tags:
  - <domain, lowercase: work | personal | ...>
  - <firstname-lowercase>
  - people
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Bump `updated:` on every edit to the page.

The `aliases` list is what makes bare-name wikilinks work. `[[Jane]]` resolves
to `jane-doe.md` because "Jane" is in its aliases. Add every variant you have
seen, including transcription-misheard versions if known.

## Body sections (use these headings in this order)

This is a LIVING profile, not a log. It answers "who this person is / how they
operate," edited in place ONLY when a durable trait, priority, or relationship
actually shifted. "What happened on `<date>`" lives in the meeting summary; the
`[[link]]` from that summary to this person IS the connection. Never copy a
meeting onto the profile, and never edit the profile just to record that a
meeting happened.

```markdown
# <First Last> - <Role>

> <One-line summary: relationship to the user, reports-to or report chain,
> email if known.>

## Role at <domain/org>

<2-4 sentences. What they own, who reports to them, scope of authority.>

## Current State

(2-4 lines, OVERWRITTEN each time it moves. What is true about them right now:
their live priorities, what they are driving, where they sit relative to the
user's work. This is the ONE place a dated marker belongs.)

What they are focused on right now: <thing>, then <thing>. As of YYYY-MM-DD.

## Working Pattern

(Durable, evidence-backed traits about how they operate. Direct? Async?
Detail-oriented? What do they hate? What signals do they reward? Each bullet is
a standing fact the user could act on, edited in place as the read sharpens,
not appended to. Cross-meeting synthesis belongs here, stated as a
present-tense fact, not as a dated log entry.)

- **<Trait>.** <Short evidence-backed explanation.>
- **<Trait>.** <Short evidence-backed explanation.>

## Quotes

(Load-bearing only. A quote earns a place here when it captures a durable
stance that recurs across meetings, not a one-off line from a single meeting.
Prune a quote when it stops being load-bearing. This is NOT a per-meeting
quote dump.)

> "<Verbatim quote capturing a standing stance.>" - <context: source link>

Meeting history: see backlinks + wiki/index.md
```

## Sizing

A fresh stub can be 30-50 lines (frontmatter + Role + Current State + one or
two Working Pattern bullets). The page should stay roughly that size and change
in place: bullets sharpen, Current State gets overwritten, an occasional
load-bearing quote earns or loses its spot. **A page that grows every ingest IS
the recap-drift smell.** If it gets longer each time you touch it, you are
logging meetings onto it instead of distilling durable facts.

## What NOT to put on entity pages

- **No "Past Discussions" / recap log.** Chronology lives in the graph:
  backlinks + `wiki/index.md`. "Which meetings involved this person" is a grep,
  not a hand-maintained list. The single static pointer line
  (`Meeting history: see backlinks + wiki/index.md`) is the only nod to it.
- **No restating org-wide context.** That belongs on a shared org/context page
  if one exists. Link, do not retype.
- **No action-item dumps.** Those live in the user's task system. Do not mirror
  them here.
- **No stacked dated updates.** When a durable fact moves, OVERWRITE the stale
  line in place and bump `updated:`. Do not append "5/29 update:" notes; the
  only dated marker belongs in Current State.
- **No speculation about psychology.** Working Pattern bullets need evidence.
  "Jane is direct" with quotes backing it is fine. "Jane is insecure about X"
  without evidence is hallucination.
