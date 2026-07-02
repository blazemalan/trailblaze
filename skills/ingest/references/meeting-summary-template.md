# Meeting summary template

Use this shape when writing or refreshing a curated meeting page at
`<Domain>/wiki/meetings/YYYY-MM-DD-<slug>.md`.

The meeting page is **not** the transcript. It is the indexed, wikilinked
digest. The raw transcript IS the verbatim record: link DOWN to it from the
meeting page, never duplicate it.

## Naming

- Date prefix: `YYYY-MM-DD-` (ISO, not US format)
- Slug: kebab-case, descriptive but short. Examples:
  - `2026-03-30-jane-1on1.md`
  - `2026-03-26-q2-planning.md`
  - `2026-04-15-marketing-huddle.md`
- If a meeting is recurring (1:1s, weekly huddles), keep the format
  consistent so pages sort and grep predictably.

## Frontmatter

```yaml
---
type: meeting
description: "<YYYY-MM-DD, who + the load-bearing outcome in one terse line; this becomes the index entry>"
date: YYYY-MM-DD
attendees:
  - [[wiki/people/jane-doe|Jane]]
  - <anyone else>
tags:
  - <domain>
  - <topic tags: 1on1, planning, budget, etc>
---
```

The `description:` is the one-liner `gen-index.py` puts in `index.md`. Write it
when you create the page so the index regenerates cleanly (never hand-edit the
index).

## Body structure

```markdown
# <Meeting name> - YYYY-MM-DD

> <One-paragraph context: what kind of meeting, why it happened, what was at
> stake. Set the scene so a future read makes sense without re-reading the
> transcript.>

## Key Points

(Bulleted, prioritized by importance. Each bullet wikilinks to the people /
concepts / projects it touches. Aim for 5-12 bullets; more than that and you
are transcribing.)

- [[wiki/people/jane-doe|Jane]] confirmed <thing>. Implication: <thing>.
- <Concept> is now at <state>. Driver: <thing>.
- ...

## Decisions Made

(Numbered. A decision big enough to be cited months later gets its own
`wiki/decisions/YYYY-MM-decision-slug.md` page that this links to. If it is
small, leave it inline here.)

1. **<Decision>** - <one-sentence summary>. See
   [[decisions/YYYY-MM-decision-slug]].
2. ...

## Action Items

(Bulleted. Each item: owner, what, by when. Flagged here for visibility; the
source of truth is the user's task system. The user routes them.)

- [ ] **<Owner>**: <action> - by <date or trigger>
- [ ] ...

## Verbatim Quotes

(Only quotes that are surprising, load-bearing, or emotionally charged.)

> "<Quote.>" - [[wiki/people/jane-doe|Jane]]

## Open Questions / What's Next

(Things that did not get resolved and need follow-up. These often become the
agenda for the next meeting.)

- <Open thread>

## Source

- Raw transcript: [[raw/transcripts/<filename>]]
- Recording (if known): <link>
- Related: [[<other meeting>]], [[<related concept>]]
```

## Sizing

- Fresh meeting summary: 50-150 lines is normal.
- Long, high-stakes meetings (offsites, board prep): up to 300 lines.
- Past 300 lines you are transcribing. The raw file IS the verbatim; strip the
  summary down to what the next session would actually need to read.

## Refreshing an existing meeting page

If a meeting already has a page (a better transcript landed, or the user added
context), update in place, do not duplicate. Bump any quotes or facts that
changed, preserve the wikilinks, and note the refresh in the log entry.
