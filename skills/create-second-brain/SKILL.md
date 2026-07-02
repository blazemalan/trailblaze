---
name: create-second-brain
description: >
  One-time setup: interview the user, then scaffold a complete second-brain
  vault (Karpathy LLM-Wiki pattern) with raw/wiki/schema layers, CLAUDE.md
  files, seed reference docs, and starter people pages. Triggers on "set up my
  second brain", "create my second brain", "build my vault", "get me started
  with Trailblaze", or a first run in an empty folder.
---

# Create Second Brain: one-time vault setup

You are about to scaffold a second brain: a personal wiki that YOU (the agent) build and maintain while the user just feeds it sources and asks questions. Based on Andrej Karpathy's LLM-Wiki pattern. Run this once per vault.

Companion skills that operate on the vault afterwards: **ingest** (file a source), **query** (answer from the wiki), **vault-lint** (health check).

## Step 0: safety check (idempotency)

Look at the target folder first.

- If it already contains a `CLAUDE.md` plus one or more `*/wiki/` folders, this is an existing vault. **Do not scaffold and do not overwrite anything.** Tell the user what you found and offer to (a) adopt it as-is, or (b) add a missing piece they ask for.
- If the folder is non-empty but clearly not a vault, confirm with the user before creating anything alongside their files.
- Only a genuinely empty (or fresh) folder gets the full scaffold.

## Step 1: the interview

Ask these one at a time, conversationally. Keep it quick; defaults in parentheses.

1. **Where should the vault live?** (default: `~/second-brain`, or the current folder if the session is already in one)
2. **What areas of your life should it cover?** These become top-level domain folders. (default: `Work` and `Personal`)
3. **What will you feed it most?** Meeting transcripts, articles, emails, PDFs? Mention the everyday flow so they can picture it: a meeting ends, they download the Google Meet transcript as Markdown, drop it in the inbox, done.
4. **Name 3-6 people who come up constantly** (boss, reports, family). You will create starter profile pages so the knowledge graph starts alive instead of empty. Get roles/relationships in one line each.
5. **Three months from now, what questions do you want this thing to answer?** ("What did X promise me?" "What is the state of project Y?") These get baked into the filing rules.
6. **Backup preference:** private GitHub repo (free, full history, needs the Obsidian Git plugin), Obsidian Sync (~$5/month, zero git knowledge), or decide later. Point to the plugin README for details either way.

Also note the user's timezone for the CLAUDE.md conventions line.

## Step 2: scaffold the tree

Create this structure (one domain block per answer to question 2; `Work` and `Personal` shown):

```
<vault>/
├── CLAUDE.md
├── log.md
├── outputs/                       # vault-wide artifacts (lint reports)
├── raw/
│   └── inbox/                     # universal drop zone, transit only
├── Work/
│   ├── CLAUDE.md
│   ├── raw/
│   │   ├── transcripts/
│   │   ├── articles/
│   │   ├── emails/
│   │   └── docs/
│   ├── wiki/
│   │   ├── sources/
│   │   ├── people/
│   │   ├── concepts/
│   │   ├── decisions/
│   │   ├── projects/
│   │   └── meetings/
│   └── outputs/
├── Personal/                      # same shape as Work
└── Reference/
    ├── quick-guide.md
    └── lint/
        ├── watchlist.md
        └── allow-list.md
```

Notes:
- Drop a `.gitkeep` in every empty folder so git-based backup preserves the tree.
- Only the raw/ subfolders matching question 3 are strictly needed, but creating all four costs nothing and avoids re-work.
- No `raw/shared/` folder: a cross-domain source gets filed in its dominant domain and wikilinks connect the rest.

## Step 3: write the vault-root CLAUDE.md

Use this template. Fill placeholders from the interview. **Hard cap 80 lines**; the vault-lint skill enforces it. This file loads at every session start, so every line costs tokens forever: keep it operational rules only.

```markdown
# Second Brain - <User's Name>

Karpathy LLM-Wiki pattern. Raw / Wiki / Schema + Action. The agent maintains the
wiki (Trailblaze skills: ingest, query, vault-lint); the human curates sources
and asks questions.

## Who <Name> is

<2-3 lines from the interview: role, org, family/context, key people. Terse.>

## Vault layout

| Folder | Layer | Notes |
|---|---|---|
| `raw/inbox/` | Raw | Universal drop zone. Transit only; agent triages at each ingest. |
| `<Domain>/raw/{transcripts,articles,emails,docs}/` | Raw | Immutable. Agent reads, never edits. |
| `<Domain>/wiki/{sources,people,concepts,decisions,projects,meetings}/` | Wiki | Agent writes. One summary per source; living profiles. |
| `<Domain>/wiki/index.md` | Wiki | GENERATED catalog. Never hand-edit; regen via gen-index.py. |
| `Reference/` | Wiki | Vault-wide: quick-guide, lint watchlist + allow-list. |
| `outputs/` (root + per domain) | Action | Produced artifacts: lint reports, briefs, deliverables. |
| `log.md` | Navigation | Append-only feed. `grep "^## \[" log.md \| tail -20` |
| `CLAUDE.md` (this + per-domain) | Schema | Operational rules. Caps: vault 80 lines, domain 60. |

## Conventions

- Files: kebab-case lowercase. Tags/metadata in YAML frontmatter, not inline.
- Wikilinks: prefer bare-name `[[Jane]]` (resolves via `aliases:`); fallback
  `[[wiki/people/jane-doe|Jane]]`. Plain-text names are invisible to the graph.
- Every wiki page carries a one-line `description:` (feeds the generated index).
- Raw is immutable. Decision pages need a named ratifier; proposals stay in
  meeting summaries until ratified.
- Timezone: <tz>.

## The three operations

- **ingest**: file new raw into the wiki. Everyday flow: meeting ends, download
  the transcript as Markdown (Google Meet, Zoom, Otter), drop it in
  `raw/inbox/`, run ingest.
- **query**: wiki-first answers with [[wikilink]] citations. Raw as last resort.
- **vault-lint**: tiered health check. Weekly standard, quarterly deep.

## What to file for

<From interview question 5: the questions this vault must answer, one per line.
The ingest edit test names one of these before touching any page.>
```

## Step 4: write each domain's CLAUDE.md

Thin schema, **cap 60 lines**, most of it grows later:

```markdown
# <Domain> - Context (thin schema)

> Thin domain schema. Vault-wide conventions live in the root CLAUDE.md.

## Layout

- `raw/{transcripts,articles,emails,docs}/`: immutable raw for this domain.
- `wiki/`: sources, people, concepts, decisions, projects, meetings + generated index.md.
- `outputs/`: produced artifacts for this domain.

## Domain notes

<Key people and their roles (from the interview). Recurring meetings. Any
sensitivity rules (e.g. personal/health content stays out of shared docs).
Grow this only when a rule earns its keep.>
```

## Step 5: seed the Reference docs

**`Reference/quick-guide.md`**: the human-facing mental model. Write it from this shape:

```markdown
# Second Brain - Quick Guide

Karpathy LLM-Wiki pattern. The agent writes the wiki; you read it through the
agent (ask questions, don't browse linearly).

## The 30-second mental model

| Layer | Who edits | What lives there |
|---|---|---|
| **Raw** | Nobody (immutable) | Transcripts, emails, decks, articles |
| **Wiki** | The agent | sources/, people/, concepts/, decisions/, projects/, meetings/ + index.md |
| **Schema** | You (rarely) | CLAUDE.md files: the rules that make the agent a disciplined maintainer |
| **Action** | You + agent | outputs/ artifacts, your task system |

## When you have X, do Y

| I have... | Do this |
|---|---|
| A meeting transcript | Download as Markdown, drop in `raw/inbox/`, run ingest |
| An article / web clip | Save to `<Domain>/raw/articles/` (Obsidian Web Clipper works great), run ingest |
| A deck or PDF | Save to `<Domain>/raw/docs/`, run ingest |
| A question | Run query: "what did Jane say about the budget?" |
| A feeling the vault is stale | Run vault-lint |
| No idea where something goes | Drop it in `raw/inbox/` and forget; the agent triages next ingest |

## The three commands

- **ingest**: file new raw into the wiki (2-4 pages touched per routine source)
- **query**: wiki-first answer with citations
- **vault-lint**: health check, report-first
```

**`Reference/lint/watchlist.md`**:

```markdown
# Lint Watchlist

Status changes the wiki must not lag behind. The ingest skill greps this before
writing any page; the vault-lint skill checks pages modified after each date.

## Departures / role changes

| Name (grep variants) | Date | Was | Notes |
|---|---|---|---|

## Name regressions

Known misspellings previously corrected vault-wide. The lint resolver greps
each bullet term below; any new hit outside log.md is a finding.

<!-- add terms as bullets, e.g.:  - Wrong Spelling -->
```

**`Reference/lint/allow-list.md`**:

```markdown
# Vault-Lint Allow-List

Known non-findings. Lint triages resolver output against this list. Propose
additions at the bottom of each lint report rather than editing mid-lint.

## Pageless-by-design wikilink targets

- (external companies/tools and one-off names that don't warrant pages)

## Structural / cosmetic

- (template placeholders inside Reference/ docs, historical log.md links)

## Page-level exemptions

- (specific rulings, with dates)
```

**`log.md`** (root):

```markdown
# Vault Log

Append-only chronological feed of agent activity. Newest at the bottom.
Entry format: `## [YYYY-MM-DD HH:MM] [domain] <operation> | <description>`

## [<now>] [vault] setup | Vault created by Trailblaze create-second-brain
→ domains: <list>
```

## Step 6: seed the people pages

For each person from interview question 4, stub `<Domain>/wiki/people/<name-slug>.md` using the ingest skill's `references/entity-page-template.md` (bundled with this plugin). Keep stubs to 10-15 lines: frontmatter (`type`, `description`, `aliases`, `tags`) + Role line + an empty Current State. **Only facts the user gave you; invent nothing.** These stubs exist so the first ingests have link targets.

## Step 7: generate the indexes

Run the ingest skill's index generator from the vault root:

```bash
python3 <plugin>/skills/ingest/scripts/gen-index.py --write all
```

Every domain gets a `wiki/index.md` cataloging its (so far sparse) pages.

## Step 8: viewing and backup

- **Obsidian**: suggest the user install Obsidian (free) and open the vault folder as an Obsidian vault. They get the graph view, backlinks, and mobile access. The agent writes; Obsidian is how the human reads.
- **Backup**, per their interview answer:
  - *GitHub path*: offer to initialize a git repo (ask before running `git init`; never push anywhere without the user's say-so). Then point them to the Obsidian **Git** community plugin for automatic interval commit+push to a **private** repo they create.
  - *Obsidian Sync path*: no git needed; they enable Sync inside Obsidian (~$5/month).
  - *Later*: fine, note it in your final report so it does not get forgotten.

## Step 9: report and first ingest

Report what you built: the tree (short form), the files seeded, and the one-line rhythm:

> Drop a source in `raw/inbox/` and run **ingest**. Ask anything with **query**. Run **vault-lint** weekly.

Then invite the first real ingest: "Got a recent meeting transcript or an article? Drop it in `raw/inbox/` and I'll walk you through the first filing."

## Discipline

- Never overwrite existing user files. Step 0 gates everything.
- Every seeded page gets a `description:` frontmatter line (the index depends on it).
- Do not install anything, run `git init`, or touch anything outside the vault folder without asking.
- Keep the whole setup conversational and fast: six questions, then build.
