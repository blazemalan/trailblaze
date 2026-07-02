---
name: ingest
description: >
  File a new raw source (meeting transcript, email, article, deck, pasted text)
  into the second-brain vault's wiki layer following Karpathy's LLM-Wiki pattern.
  A routine meeting touches 2-4 pages (summary + the pages it genuinely moves);
  only landmark sources touch more. Triggers on "ingest this", "process this",
  "file this", pasted transcripts, or new files in raw/inbox/ or any per-domain
  raw/ folder.
---

# Ingest: file a new raw source into the wiki

Karpathy LLM-Wiki ingest. A new raw source needs to be filed into the wiki layer. The point of ingest is making the source **answerable later**; the meeting summary plus wikilinks usually achieves that on its own. Fan-out to other pages happens only when the source genuinely *moves* them; the graph compounds through links, not page edits.

**Page budget (calibration, not a hard cap):** a routine meeting = the summary + a project thread if it is a program 1:1 + *maybe* one concept/status page. That is 2-4 pages. If you are about to touch 6+, stop and re-check each edit against the test below. (The classic failure mode: editing a person's page on every ingest while almost none of those edits change a durable fact. The budget kills that.)

**The edit test, applied before EVERY page edit outside the summary:** *name the future question the user would ask where this edit (not the meeting summary, not a backlink) is the thing that answers it.* Cannot name one? Do not touch the page. Real queries are meeting prep, "what did we decide," "what is the state of X," and drafting help. File for those, not for encyclopedic completeness.

```
RAW    - immutable. Read it. NEVER edit.
WIKI   - write here. sources/, people/, concepts/, decisions/, projects/, meetings/.
SCHEMA - CLAUDE.md files. Don't touch.
ACTION - the user's task list, outputs/. Don't touch from ingest.
```

**Scripts:** this skill bundles deterministic helpers in its `scripts/` folder (in Claude Code: `${CLAUDE_PLUGIN_ROOT}/skills/ingest/scripts/`; on other surfaces, the `scripts/` folder next to this SKILL.md). Run them with `python3` **from the vault root**; they treat the working directory as the vault (`VAULT_ROOT` env var overrides).

## Inputs

- **Source path**, usually `raw/inbox/`, a per-domain `raw/` folder, or pasted inline.
- **Domain**, one of the vault's domain folders (listed in the vault CLAUDE.md; a domain is any folder containing a `wiki/`). Infer from the source path; if ambiguous, deduce from content or ask once.

## Pre-flight (cost-conscious)

Read these. Skip everything else unless needed.

1. **Vault-root `CLAUDE.md`** and the **domain's `CLAUDE.md`** if it has one. Always. They are size-capped so the cost is bounded.
2. **Project rules doc** (`wiki/projects/<X>/program-rules.md` or similar), ONLY if the source touches a project that declares one.
3. **Roster/directory pages** (people directory, org page, glossary), ONLY when you spot an unfamiliar name in the source. Do not pull them defensively.
4. **`references/entity-page-template.md` / `references/meeting-summary-template.md`** (bundled with this skill), ONLY when stubbing a new page. Do not pull when only updating existing pages.

The conditional reads are how this skill stays cheap. Defensive reads are the main token-cost driver in ingest workflows.

## Detect unprocessed sources (run at every ingest invocation with no args)

When ingest fires without a specific path, scan **all raw locations**, not just the inbox:

1. **`raw/inbox/`**, the transit zone. Files here need triage + ingest.
2. **Per-domain `raw/` subfolders** (transcripts, articles, emails, docs), files dropped directly by the user's transcription pipeline or web clipper.

Run the triage script; it classifies every raw file BEFORE any LLM read, so empty stubs and duplicates cost zero tokens:

```bash
python3 <skill>/scripts/triage.py
# EMPTY        -> failed recording (0:00 / no content), propose delete, don't read
# JUNK?        -> mic-test or trivial stub, propose delete
# DUPLICATE?   -> a wiki page already exists for its date, confirm before ingest
# UNPROCESSED  -> genuinely new, read + ingest
# CLEAN        -> nothing to do
```

Trust EMPTY/CLEAN verdicts without opening the files. DUPLICATE? still gets a quick content check (re-transcriptions of the same meeting are skipped; a different same-day meeting is ingested).

Surface to the user: *"Found N unprocessed file(s), want me to ingest? [list]"* Never auto-ingest without confirmation.

**Inbox flow (transit zone, files should not sit here):**

1. **Triage move BEFORE ingest.** Move each file from `raw/inbox/` to its proper home (use `git mv` if the vault is a git repo):

   | Source kind | Destination |
   |---|---|
   | Meeting transcript / auto-notes (Google Meet, Zoom, Otter, Granola, manual) | `<Domain>/raw/transcripts/<filename>.md` |
   | Email thread | `<Domain>/raw/emails/<filename>.md` |
   | Deck / PDF / doc | `<Domain>/raw/docs/<filename>` |
   | Article / web clip | `<Domain>/raw/articles/<filename>.md` |
   | Genuinely cross-domain | file in the dominant domain; wikilinks connect the rest |

2. Run the workflow below.
3. Append a log entry.

The vault-lint skill flags any file sitting in `raw/inbox/` more than 7 days.

## Workflow

### 1. Read the source end-to-end

Do not skim. A transcript's load-bearing details are often in throwaway moments. If you summarize without reading, you will miss the quote that mattered.

### 2. Identify

- **People**: full names, roles, relationships. Verify spelling against canonical sources (see `references/canonical-sources.md`) if any name is unfamiliar.
- **Concepts**: programs, projects, tools, frameworks, decisions in flight.
- **Decisions**: see the decision-page bar below.
- **Action items**: flag in your final report; do NOT write to the user's task system.
- **Verbatim quotes**: surprising, load-bearing, emotionally charged. Attribute. Never fabricate.

### 3. Create the canonical wiki summary page: ONE per source, shape depends on source type

Karpathy is two layers: raw + wiki. Each raw source gets **one** wiki summary file, not two:

| Source kind | Canonical summary page |
|---|---|
| Meeting / 1:1 / call transcript | `wiki/meetings/YYYY-MM-DD-<slug>.md` (step 7 below). **Do NOT create a separate `wiki/sources/` page.** |
| Article / web clip / blog post | `wiki/sources/<slug>.md` |
| Deck / PDF / whitepaper | `wiki/sources/<slug>.md` |
| Email thread | `wiki/sources/<slug>.md` |
| Pasted notes (non-meeting) | `wiki/sources/<slug>.md` |

**Rule:** if it is a meeting, the meeting page IS the source page. Splitting them creates ~70% overlap, two files to keep in sync, and inevitable drift.

For non-meeting sources, write to `wiki/sources/<slug>.md` with frontmatter:

```yaml
---
type: source
description: "<one terse line; becomes the index entry>"
source_file: <path/to/raw/file>
source_kind: article | deck | email | notes
tags: [domain, topic-tags]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Then: `# Title` · `## Summary` (3-5 bullets) · `## Key Claims` · `## Entities Mentioned` (with wikilinks) · `## Concepts Covered` (with wikilinks). Factual only; interpretation lives on concept/decision pages.

### 4. People pages: always current, never growing (the Wikipedia rule)

The page is the source of truth for the person's **current state**: role, reporting line, relationship to the user, how they operate, what they are driving. When the source moves any of those, UPDATE the page; freshness is the point. The discipline is **how**, and these rules are mechanical so they hold on any model:

1. **Overwrite, never append.** Every edit replaces the line it supersedes, in place. **Net line count must not grow.** Adding a line means deleting/merging the stale one it replaces. (Exceptions: brand-new page stub; a structurally new fact with no predecessor, e.g. a first direct report.)
2. **No dates, no "said."** If your new line contains a meeting date or narrates what someone said/did in a meeting, it belongs in the meeting summary, not here. (The Quotes section is the exception, and it swaps: one quote in, weakest quote out.)
3. **Current priorities: max 5 bullets.** New priority in, stalest priority out.
4. Bump `updated:` whenever you touch the page.

**Trigger test (token-efficiency rule): edit a people page only when the source makes something on it FALSE.** Role changed, person departed, reporting line moved, a listed priority is dead. "New info exists" is not a trigger; "the page now lies" is. If the source changes nothing about current state, the meeting summary's `[[wikilink]]` IS the filing. Touch nothing.

**You cannot detect a lie without looking.** For each person with a *speaking/deciding* role in the source (not mere mentions), grep their page's Current State / role lines against what the source says: a cheap grep, not a full read. Restraint applies to *writing*, never to *checking*.

**Ledger pages are exempt from touch-nothing.** Some pages exist to accumulate; route matching content to them as part of every ingest: a wins/highlights ledger, a glossary (new acronyms/nicknames), an org roster (staffing changes), project 1:1 threads. Dated entries are correct there; they are ledgers, not state pages. The vault-lint skill flags people pages that grew past 150 lines or picked up dated event-narration lines.

New pages: stub from `references/entity-page-template.md`, 30-50 lines. A home for durable facts, not a meeting log. Prefer bare-name wikilinks `[[Jane]]` (they resolve via `aliases:`); fallback to the path form `[[wiki/people/jane-doe|Jane]]`.

### 5. For each concept: update ONLY IF its state changed

Same pattern at `<Domain>/wiki/concepts/<slug>.md`. Overwrite the current state in place when it moved; do not stack dated update notes. Exception: a concept whose *evolution is itself the knowledge* (a decision in flight) may carry **one** short dated note marking the turn, but prune superseded notes as you add new ones, so the page reads as current state, not a changelog. If state did not move, touch nothing.

### 6. For each decision: check the bar BEFORE writing a decision page

A decision page is for **ratified, citable, hard-to-reverse outcomes only.** All three must hold:

1. **Authoritative.** A person with authority committed. *"Verbal yes, written sign-off pending"* fails.
2. **Hard to reverse.** Reopening requires a formal conversation, not "let's revisit next week."
3. **Will be cited later.** Six months from now, someone asks *"didn't we decide X?"* and this page settles it.

**If any are missing, it is NOT a decision page.** It is a proposal in flight. File it in the meeting summary's `## Decisions` section, a project 1:1 thread, or the project's status page. **Promote to a decision file ONLY when the ratifier signs off.** When the bar IS met, capture: what · by whom (with named ratifier) · alternatives considered · why this won · what would trigger reopening.

### 7. Meeting summary (if the source is a meeting)

**Multi-part recordings are ONE meeting.** `Part 1`/`Part 2` filenames sharing a date get a single summary page covering all parts; list each raw file in the Source section. Never one page per part.

`<Domain>/wiki/meetings/YYYY-MM-DD-<slug>.md`, shaped per `references/meeting-summary-template.md`: Frontmatter → Context → Key Points → Decisions Made → Action Items → Source (link DOWN to raw). **Cap: 150 lines.** If you are approaching it, you are transcribing, not synthesizing; the raw IS the verbatim record.

### 8. Project thread (if the source is a 1:1 inside a project)

When the source is a recurring 1:1 in a project that declares a `1on1s/` convention in its rules doc, update `wiki/projects/<X>/1on1s/<firstname>.md`. Add a tight program-scoped section: link to the meeting summary · program-relevant decisions only · action items affecting the program.

**"Patterns observed" bullets must be operational, not observational.** Every bullet has to pass: *would reading this before the next 1:1 change a question the user asks or an action they take?* If no, delete. Lines like "self-models the learning phase" are LLM narration, not patterns.

### 9. Regenerate `wiki/index.md` (never hand-edit it)

`index.md` is **generated** from each page's `description:` frontmatter. So:

1. **Every page you created or edited must carry a `description:`** one-liner (terse, factual, under ~30 words, leads with the entity/topic). If you forgot, set it deterministically: `python3 <skill>/scripts/set-description.py <page.md> --text "..."`.
2. **Regenerate:** `python3 <skill>/scripts/gen-index.py --write <domain>` (domain folder name, or `all`). The index is a complete catalog of every wiki page; the script rebuilds it, so it cannot drift or be forgotten.

The vault-lint skill flags a stale index (committed differs from regen) and any indexed page missing a `description:`.

### 10. Append a log entry

To `log.md` at the vault root:

```
## [YYYY-MM-DD HH:MM] [domain] ingest | <short description>
→ pages touched: [[link1]], [[link2]], ...
→ source: <path to raw>
```

Use the user's local timezone. **Keep it to ONE tight line of description**; the log is read via `tail`, so a verbose paragraph taxes every reader.

Then trim the log so it stays lean: `python3 <skill>/scripts/log-rotate.py` (keeps the last 60 entries in `log.md`, rolls older ones into `log-archive.md`; idempotent). `triage.py` reads both files, so re-ingest detection is unaffected.

### 11. Report back to the user

**Cap: 10 lines.** What got filed (created vs updated, with links). Anything needing a human decision ("stubbed Person X, spelled right?"). Action items spotted that belong in the user's task system (flag, do not write).

## Discipline rules

- **Raw is immutable.** Typos and diarization errors stay in the raw file. The fix lives in the wiki summary.
- **Wikilinks everywhere.** Every reference to a person/concept/decision/project links to its page. Plain-text names are invisible to the graph.
- **One editable home per fact; compound through links, not copies.** "What happened on `<date>`" → the meeting summary (one distillation) + the immutable raw. "Who someone is / how they operate" → their profile, a living page edited in place ONLY when a durable trait/priority/relationship shifts. "Which meetings involve them" → the graph: backlinks + grep + `index.md`, zero maintenance. Never copy a meeting onto a profile; never edit a profile just to log a meeting.
- **Wiki pages stay tight.** 50-150 lines is the band for most pages. Prune stale claims as you add new evidence.
- **Preserve verbatim quotes when load-bearing.** Do not paraphrase quotes. Do not quote noise either.
- **Never fabricate quotes or attributions.** If it is not in the source, it does not go on the page.
- **Status check before writing.** Grep every page you are about to touch against `Reference/lint/watchlist.md` (departures / role changes); never present a departed person as active. Annotate ("departed 6/2") or use past tense. When a source reveals a NEW departure or role change, add it to the watchlist. This kills the most common lint finding at the source.
- **Never auto-write to the user's task system.** Flag action items in your report; the user routes them.
- **No subagents for single-source ingest.** Each subagent re-loads schema, which multiplies cost. Subagents are for batch backfills only.

## When NOT to ingest

- Source already in the wiki (check `sources/`, `meetings/`, `decisions/` for a date/slug match).
- Source is pre-ingested raw with no new evidence.
- The user is asking a question, not filing a source → use the query skill instead.
- The "source" is a one-line task → it goes to the user's task system, not the wiki.

## Supporting references (bundled with this skill)

- `references/entity-page-template.md`: shape for new `wiki/people/*.md`
- `references/meeting-summary-template.md`: shape for `wiki/meetings/*.md`
- `references/canonical-sources.md`: name/concept validation checklist

Read only when stubbing a new page (templates) or when an unfamiliar name appears (canonical sources).
