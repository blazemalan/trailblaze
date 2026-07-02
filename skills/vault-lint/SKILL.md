---
name: vault-lint
description: >
  Tiered health check on a Karpathy LLM-Wiki second-brain vault: quick
  (deterministic resolver only), standard (resolver + judgment checks on files
  changed since the last pass, the weekly default), deep (full-vault sweep,
  quarterly). Report-first; a "--fix" arg or explicit user go-ahead runs the
  mechanical fix phase after the report is saved. Triggers on "lint the vault",
  "vault health check", "vault audit", or a scheduled weekly review.
---

# Vault Lint: LLM-Wiki health check

Lint surfaces drift and rot so the user decides what to fix. **Report first, untainted**: discovery never edits. The fix phase runs only after the report is saved, and only with `--fix` or an explicit go-ahead.

**Scripts:** the deterministic resolver lives in this skill's `scripts/` folder (in Claude Code: `${CLAUDE_PLUGIN_ROOT}/skills/vault-lint/scripts/`; on other surfaces, the `scripts/` folder next to this SKILL.md). Run it with `python3` **from the vault root** (`VAULT_ROOT` env var overrides).

## Run tiers

| Tier | What runs | When |
|---|---|---|
| `quick` | resolver script only | ad-hoc "is the vault clean?" |
| `standard` (default) | resolver + judgment checks scoped to files modified since the last report + carry-forward diff (first pass ever: the whole vault is the change set) | weekly |
| `deep` | full-vault judgment sweep | quarterly, or on request |

Clean checks stay clean; rot accrues on edited pages. That is why `standard` scopes to the change set (`git log --since=<last report date> --name-only` when the vault is a git repo; otherwise files with a recent modified time).

## Step 0: mechanics (every tier)

1. From the vault root: `python3 <skill>/scripts/resolver.py <temp-path>/vault-lint-resolver.json` (any scratch/temp location your environment allows). Deterministically covers checks 1, 4, 6, 7, 9, 10 plus name regressions, the recap-drift hard signal, basename collisions, and file counts. Zero tokens; comparable across runs.
2. If the vault is a git repo, snapshot `git rev-parse HEAD` + `git status --short`. A dirty tree can mean another session is working: note it in the report header and re-verify findings against the live tree just before writing.
3. Load `Reference/lint/allow-list.md` (in the vault): known non-findings. Do not re-litigate them; propose additions at the bottom of the report.
4. Load the prior ledger (`vault-lint-*.findings.json` next to the last report) and diff statuses mechanically: resolved / open / regressed. Do not re-derive carry-forwards from prior report prose.

## Scope

Wiki + schema layers: every domain's `wiki/`, `Reference/`, the root `index.md` if one exists, and the CLAUDE.md cascade. **Never scan:** `raw/`, `archive/`, `outputs/`, `.obsidian/`, `.claude/`, `Templates/`, the user's task files, `.git/`. Respect user scoping ("lint Work only") and note it in the header.

## The 11 checks

Procedures and proven one-liners: `references/check-queries.md` (most are automated by the resolver; use the file for ad-hoc spot checks). Evidence discipline: every finding cites file:line + the exact claim. A clean check is reported as clean. Report-bucket mapping: Error → Critical, Warning → Medium; Low is the residual bucket for cosmetic items the resolver surfaces outside the numbered checks (e.g. risky basename collisions). In a young vault with only a handful of meeting/source files, treat check 5's "2+ files" bar as "a clearly-roled name recurring across what files exist" and list candidates as next-pass items.

1. **Broken wikilinks (Error)**: from the resolver; triage unresolved targets against the allow-list; suggest concrete retargets (search for the likely intended file before proposing a de-link).
2. **Contradictions (Error)**: same fact, same time, different pages, no was/now reconciliation. Newer-supersedes-older = stale (check 3), not contradiction.
3. **Stale claims (Warning)**: claims >30 days old where a newer source disagrees. **3a. Status-lag (mechanical-first):** grep names from `Reference/lint/watchlist.md` (departures / role changes) across pages modified *after* each change date; unannotated active-tense mentions are findings. Run this every tier; it is historically the #1 recurring finding class.
4. **Orphan pages (Warning)**: from the resolver, collision-aware. Bare-basename links can mis-credit colliding files, so confirm with contextual greps before flagging. Note the generated `index.md` does not count as an inbound link (it lists every page), so the orphan list reflects *real* cross-references.
5. **Missing entity pages (Warning)**: names in 2+ meeting/source files with no page/alias; cross-check any roster/directory page the vault keeps. Never auto-stub during lint.
6. **Meeting → Source (Warning)**: resolver flags meeting summaries missing a `## Source` section (or a "raw not preserved" note).
7. **Stale inbox (Warning)**: resolver flags non-`.gitkeep` entries older than 7 days.
8. **Drift from canonical (Warning)**: anchors are the vault's canonical reference docs (e.g. a voice guide, north-stars doc, role definition, roster) as listed in the vault CLAUDE.md. Date-stamped / was-now pages are not silent drift.
9. **CLAUDE.md size/placement (Error/Warning)**: resolver reports line counts. Caps: vault root 80 lines, domain 60. Flag rogue CLAUDE.md files deep in the wiki cascade.
10. **Index staleness + description coverage (Warning)**: `index.md` is GENERATED by the ingest skill's `gen-index.py` from each page's `description:` frontmatter. The resolver flags any committed index that differs from a fresh regen (stale → run `gen-index.py --write`) and lists indexed pages missing a `description:` one-liner. Fix = regenerate / add the missing description. Never hand-edit the index.
11. **Recap drift (Warning)**: hard signal from the resolver (chronological-log headings on people/concepts pages); soft signal (dated event-narration bullets on living profiles) read only within the change set. Durable traits citing dates are fine; dated event narration is not.

## Agents & cost

- Judgment finders run on the session model; **adversarial verification runs on a cheaper model and only for Error-severity findings.** Warnings ship on finder evidence with cites.
- `standard` should rarely need more than ~6 agents. `deep` is the only fleet-scale run; confirm with the user before launching one.

## Output

1. Report → `outputs/vault-lint-YYYY-MM-DD.md` at the vault root (append `-passN` if same-day). Structure: `references/report-template.md`.
2. Ledger → same basename + `.findings.json`: `[{id, check, severity, title, files, status: open|fixed|deferred, first_seen, last_seen}]`. Keep IDs stable across passes; the next pass diffs this file.
3. Conversation summary: headline counts, top 1-3 fixes, report path. Then ask *"Want me to fix any of these?"*, unless `--fix` was given.

## Fix phase (`--fix` or explicit go-ahead)

- Runs **after** the report + ledger are saved. Never during discovery.
- In scope (mechanical): broken-link retargets, alias additions, index regeneration (`gen-index.py --write`), status/date-stamp annotations, was/now notes, entity stubs the report recommended. Exact-match edits only; they fail safely against concurrent sessions.
- Out of scope (mark `deferred` in the ledger with what is needed): anything requiring the user's knowledge (role confirmations, name spellings), anything in `raw/` or `archive/`, deletions, rewrites of judgment content.
- Afterwards: re-run the resolver, confirm **0 new breaks**, append a "Fix pass" section to the report, update ledger statuses, add a `log.md` entry.

## Discipline

- Conservative on contradictions; default to stale when newer overrode older.
- No raw or archive. No fabricated findings. Acknowledge clean checks explicitly.
- New departures / role changes discovered mid-lint: add to `Reference/lint/watchlist.md`.

## Cadence

Weekly `standard` (schedule it if your surface supports scheduled tasks) · `deep` quarterly.
