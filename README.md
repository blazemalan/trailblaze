# Trailblaze -- Second Brain

**Your second brain: a personal wiki that an AI agent builds and maintains for you.**

You feed it sources (meeting transcripts, articles, emails) and ask it questions. The agent does everything else: summarizing, cross-referencing, filing, and keeping it all current. Chat memory forgets; this compounds.

Trailblaze packages the whole system as a Claude plugin: one skill scaffolds your vault, and three more run it day to day.

> **Why "Trailblaze"?** The pattern's ancestor is Vannevar Bush's 1945 Memex, a machine for blazing associative trails between documents. Wikilinks are exactly those trails. This implementation traces back through [Andrej Karpathy's LLM-Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) ([github.com/karpathy](https://github.com/karpathy)), which this plugin is built on.

## The idea in 30 seconds

Most "chat with your documents" tools are RAG: the model re-derives the answer from raw chunks on every question, and nothing accumulates. The LLM-Wiki pattern is different. The agent **incrementally builds and maintains a persistent, interlinked Markdown wiki** that sits between you and the raw sources. Knowledge is compiled once and kept current, not re-derived every time.

| Layer | Who edits it | What lives there |
|---|---|---|
| **Raw** | Nobody (immutable) | Transcripts, emails, decks, articles: your source of truth |
| **Wiki** | The agent | People pages, concept pages, meeting summaries, decisions, an index |
| **Schema** | You (rarely) | CLAUDE.md files: the rules that make the agent a disciplined maintainer |

Three operations run the whole thing: **ingest** (file a source), **query** (answer from the wiki, with citations), **lint** (periodic health check). Good answers get filed back into the wiki, so your explorations compound too.

## Install

Trailblaze works in the Claude apps (web chat, Claude Desktop, and Claude Cowork) and in Claude Code. Plugins require a paid Claude plan.

**Claude apps:**

1. Open **Customize → Plugins**.
2. Add this repository as a marketplace (GitHub repo or git URL), or upload the plugin folder directly.
3. Install **Trailblaze**.

**Claude Code:**

```
/plugin marketplace add blazemalan/trailblaze
/plugin install trailblaze@trailblaze
```

## Quickstart

1. Create an empty folder where your second brain should live (for example `~/second-brain`) and open a Claude session there (in Cowork or Claude Code, work in that folder).
2. Run the **create-second-brain** skill: "set up my second brain".
3. Answer six quick questions (your life domains, what you'll feed it, the people who matter, the questions it should answer).
4. The agent scaffolds the vault: folders, CLAUDE.md rules, a quick-start guide, starter pages for your key people, and a generated index.

Then the everyday rhythm:

- **Meeting ends** → download the transcript as Markdown (Google Meet, Zoom, Otter, whatever you use) → drop it in `raw/inbox/` → run **ingest**.
- **Have a question** → run **query**: "what did Jane say about the budget?" You get an answer with links to the exact pages it came from.
- **Once a week** → run **vault-lint** for a health report (broken links, stale claims, contradictions, pages drifting from the rules).

## The four skills

| Skill | What it does |
|---|---|
| `create-second-brain` | One-time setup: interview → scaffold the vault |
| `ingest` | File a raw source into the wiki. Disciplined: a routine meeting touches 2-4 pages, profiles stay current instead of growing forever, and a triage script skips empty or duplicate files before any tokens are spent |
| `query` | Wiki-first answers with `[[wikilink]]` citations. Deterministic search and backlink scripts run before any expensive reading |
| `vault-lint` | Tiered health check (quick / standard / deep). Report-first; fixes only run when you say so |

## Plugins in this repo

This marketplace ships two plugins:

- **Trailblaze** (the four skills above) — build and run the second brain.
- **[The Grid](plugins/grid/README.md)** — a live 3D mind-graph of your vault that lights up in real time as a Claude Code agent reads and edits your notes. You watch it think. Say "set up the grid" to install.

## Why this stays cheap

Most agent-maintained knowledge bases die of token cost: the agent re-reads everything, appends forever, and every month the system gets slower and more expensive. Trailblaze ports the cost discipline from a production vault that runs this pattern daily:

- **Scripts before tokens.** Bundled Python does the mechanical work for free. `triage.py` classifies every raw file (empty recording? duplicate? already filed?) before the agent reads a single line. `search.py` and `backlinks.py` pick the candidate pages before any reading happens. The lint resolver runs six of the eleven health checks with zero model involvement.
- **Questions hit the wiki, not the raw pile.** The wiki is the compressed, already-cross-referenced answer, so a typical query costs a few thousand tokens instead of a hundred thousand. Raw transcripts are a last resort, and needing one is treated as a signal that the wiki has a gap to fix.
- **Writes are budgeted.** A routine meeting touches 2-4 pages, and every edit outside the summary must name the future question it answers. Profile pages are living documents with a no-net-growth rule: new facts overwrite stale lines instead of stacking dated updates. Meeting summaries cap at 150 lines. Pages that never grow stay cheap to read forever.
- **Nothing to hand-maintain.** The per-domain index is generated from page frontmatter, so it cannot drift or be forgotten. The activity log auto-rotates at 60 entries so tailing it stays fast.
- **A bounded always-on footprint.** The vault's rule files (CLAUDE.md) are hard-capped at 80 lines for the root and 60 per domain, and lint enforces the caps, so session-start cost never creeps. The plugin itself adds roughly 600 tokens to a session; skill bodies load only when a skill actually fires.

The net effect: the vault gets more valuable every week while the cost per question stays flat. It also means the skills run fine on smaller, cheaper models, because the discipline lives in procedures and scripts, not in model heroics.

One practical note: the scripts need a surface that can run Python (Claude Cowork, Claude Desktop, or Claude Code). In plain web chat the skills still work; the agent just does those steps manually.

## Viewing your vault: Obsidian

The vault is plain Markdown folders, so any editor works, but [Obsidian](https://obsidian.md) (free) is the recommended window into it: graph view, backlinks, instant search, and mobile apps. The division of labor is simple: the agent writes the wiki, Obsidian is how you read it. The [Obsidian Web Clipper](https://obsidian.md/clipper) browser extension is also the easiest way to save articles into your raw folders.

## Backing it up

Two good options, both independent of the agent:

- **GitHub (free).** Create a **private** repository and install the Obsidian **Git** community plugin, which auto-commits and pushes on an interval. You get full version history for free. This is how the author runs his own vault.
- **Obsidian Sync (~$5/month).** Zero git knowledge required, end-to-end encrypted, and it syncs your phone too. Turn it on inside Obsidian.

Either way: your second brain will eventually hold things you care about. Set up one of these in week one.

## Not using Claude?

The pattern is bigger than any one tool. Karpathy's [original idea file](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) is written to be pasted into any capable agent, and the four `skills/*/SKILL.md` files in this repo are plain Markdown instructions you can adapt to other agents (the schema file just becomes AGENTS.md instead of CLAUDE.md).

## Credits

- Pattern: [Andrej Karpathy's LLM-Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Lineage: Vannevar Bush's Memex (1945)

MIT licensed. Built by [Blaze Malan](https://www.linkedin.com/in/blazemalan/), generalized from the vault he runs daily.
