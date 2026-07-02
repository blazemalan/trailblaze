---
name: query
description: >
  Answer a question against the second-brain vault's wiki layer. Wiki-first
  discipline: read the per-domain index.md, follow into entity/concept/meeting/
  decision pages, drop to raw transcripts ONLY as a last resort. Triggers on
  questions like "what do I know about X", "what did [person] say about Y",
  "find that doc about Z", or any free-text question that should be answered
  from the vault rather than the web. Synthesizes with wikilink citations.
---

# Query: wiki-first answers from the second brain

The query side of Karpathy's LLM-Wiki. The wiki was compressed precisely so questions cost ~5K tokens, not ~100K. **Wiki first. Raw only as last resort.**

**Scripts:** this skill bundles deterministic helpers in its `scripts/` folder (in Claude Code: `${CLAUDE_PLUGIN_ROOT}/skills/query/scripts/`; on other surfaces, the `scripts/` folder next to this SKILL.md). Run them with `python3` **from the vault root** (`VAULT_ROOT` env var overrides).

## When to use this skill

- Free-text questions about people, projects, decisions, recent meetings, history, or context that lives in the vault.
- "What did Jane say about the budget?" · "When did X get decided?" · "What's the current state of project Y?" · "Find the doc about Z."

**Do NOT use for:**
- A new raw source to file → the ingest skill
- A health check / audit → the vault-lint skill
- Drafting content on the user's behalf → a direct request, not a vault query

## Domain detection

Infer the question's domain from the people and topics mentioned; the vault-root `CLAUDE.md` lists the domains and what lives in each. If genuinely ambiguous, ask once. If cross-domain, query both and note it in the answer.

## Search strategy

### 0. Deterministic scripts BEFORE any reading or agent fan-out (zero tokens)

```bash
# Top-8 candidate pages for the question's keywords (filename/H1/aliases/description/tags/body scoring)
python3 <skill>/scripts/search.py <keyword> [keyword ...] [-n 8]

# "Which pages link to X": the most common query shape, one script run instead of a vault grep
python3 <skill>/scripts/backlinks.py <page-slug-or-alias>
```

Read ONLY the files these return (plus the index if needed). When the scripts return good candidates, steps 1-2 below collapse into "read what they returned, following the per-question patterns"; walk steps 1-4 manually only when the scripts come back empty or the question is synthesis-shaped rather than lookup-shaped. **Never launch a search agent before running search.py.**

### 1. Start with the per-domain `wiki/index.md`

Read the index for the relevant domain (`<Domain>/wiki/index.md`). Scan the section headers (Sources / People / Concepts / Decisions / Projects / Meetings) for entries matching the question. Index entries are one-liners; match on keywords + topic.

### 2. Read the candidate wiki pages

Pull the matched pages. Common patterns:

- **Person question** → `wiki/people/<name>.md` first, then follow links to recent meetings/decisions they are tagged in.
- **Project question** → `wiki/projects/<slug>.md` (or the project's status page for in-flight items, its rules doc for operational guardrails).
- **Decision question** → `wiki/decisions/` for ratified outcomes. For in-flight proposals, check the relevant project 1:1 thread or recent meeting summaries.
- **"What did X say about Y"** → `wiki/people/<X>.md` → linked meetings → `wiki/meetings/YYYY-MM-DD-<topic>.md`.
- **Historical context** → `wiki/sources/` (one summary per ingested source) or grep `log.md`.

Follow `[[wikilinks]]` to pull related context. Read enough to answer thoroughly. **Do not read the entire wiki; read the candidate pages and stop.**

### 3. Drop to raw, only as last resort

If the wiki pages do not have the answer:
- Check `wiki/sources/<slug>.md` summaries (they distill raw content).
- Only THEN open files in `raw/transcripts/`, `raw/emails/`, etc.

90% of questions resolve in step 2. If you find yourself opening raw transcripts to answer a question, the wiki probably has a gap: flag it in your answer ("the wiki doesn't capture this yet, pulling from raw...").

### 4. Use `Reference/` for vault-wide context

Vault-wide docs (the user's preferences, writing voice, north stars, people directory, glossary) live in `Reference/` if the user keeps them. Check there for questions about the user themselves or cross-domain conventions.

## Synthesize the answer

### Format

Match the answer shape to the question:

- **Factual** → direct answer with citations.
- **Comparison** → table or structured comparison.
- **Exploration** → narrative with linked concepts.
- **List / catalog** → bulleted list with brief descriptions.

### Citations

Every factual claim cites the wiki page it came from using a `[[wikilink]]`. Example:

> Per [[wiki/people/jane-doe|Jane]]'s [[2026-05-14-jane-1on1|5/14 1:1]], the candidate metric is **X, 12 → 18 by Q4**. Not yet ratified; sign-off pending ([[wiki/projects/metrics/1on1s/jane|jane.md]]).

### When the wiki does not have the answer

State it plainly. Never invent. Suggest the next move:
- *"The wiki doesn't have <X>. The raw transcript at `<path>` likely covers it. Want me to read it?"*
- *"No wiki page exists for <X> yet. Want me to stub one?"*

### Offer to save valuable answers

If the answer produces something durable (a comparison, an analysis, a new connection), offer:

> "This comparison might be worth keeping. Want me to file it as `wiki/concepts/<slug>.md`?"

If yes: create the page with frontmatter (`description`, `tags`, `sources`, `created`, `updated`), regenerate the index (`gen-index.py --write <domain>`, bundled with the ingest skill), and append a `## [YYYY-MM-DD] query | <topic>` line to `log.md`. Do not save trivia or single-fact answers; only synthesis worth re-reading. This is how explorations compound instead of disappearing into chat history.

## Discipline

- **Wiki first, always.** Resist the urge to grep raw transcripts. The wiki was built to be the answer.
- **Cite everything.** No claim without a wikilink to its source.
- **Never invent.** If you did not find it, say so.
- **Bare-name wikilinks resolve** via `aliases:` frontmatter, so `[[Jane]]` is fine.
- **Be tight.** Most queries deserve a 3-10 line answer. Long structured answers are for genuinely complex questions.

## Related skills

- **ingest**: file new raw into the wiki (use when the question requires evidence the wiki does not have yet)
- **vault-lint**: health-check the wiki (use when queries keep coming up dry, which indicates wiki rot)
