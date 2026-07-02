# Vault-Lint Report Template

Use this scaffold; populate from the checks. Keep it skim-friendly: the user
reads this in a short window, not as a research doc.

## Frontmatter

```yaml
---
type: lint-report
generated: YYYY-MM-DD HH:MM
scope: WIKI layer + Reference + schema (excludes raw/, archive/, outputs/)
files_audited: <integer count of .md files lint actually read>
pass: <integer if this is a re-run on the same day; omit otherwise>
---
```

## Body sections (in this order)

```markdown
# Vault Lint Report - YYYY-MM-DD

<One-line context: "First pass" / "Weekly lint" / "Post-cleanup re-run",
situates the report in the bigger arc.>

## Summary

| Severity | Count | Status |
|---|---|---|
| **Critical** | <n> | <one-line characterization, or "none"> |
| **Medium** | <n> | <one-line> |
| **Low** | <n> | <one-line> |
| Orphan pages | <n> | <"every wiki page has inbound links" or count> |
| Name regressions | <n> | <"holding" or list> |

## Critical

<For each critical finding: a ### subsection with file paths, the claim, and a
one-line suggested fix. Omit this section entirely if zero criticals, but
still list "Critical | 0" in the summary table.>

## Medium

<Same shape. Historically common medium findings: meetings missing `## Source`,
candidate missing entity pages, stale claims.>

## Low

<Same shape. Examples: paraphrase-risk quotes, bare wikilinks for
low-frequency unverified names.>

## Healthy checks

<Bulleted list of checks that passed clean. The absence of findings is signal;
call it out explicitly.>

- 0 broken wikilinks
- 0 orphan wiki pages
- 0 name regressions
- All <N> meetings have ## Source sections
- All entity pages have type: frontmatter + aliases: for bare-name resolution
- CLAUDE.md files within size caps

## Final wiki state

| Layer | Count |
|---|---|
| <Domain>/wiki/people/ | <n> entity pages |
| <Domain>/wiki/concepts/ | <n> concept pages |
| <Domain>/wiki/decisions/ | <n> decision pages |
| <Domain>/wiki/projects/ | <n> project files |
| <Domain>/wiki/meetings/ | <n> (<n> have ## Source) |
| log.md entries | <n> |

(One row group per domain; counts come straight from the resolver output.)

## What changed since the prior pass

<Only include when a prior report exists. Diff the headline counts.>

| Metric | Prior pass | This pass |
|---|---|---|
| People pages | <prev> | **<curr>** (+<delta>) |
| Broken wikilinks | <prev> | **<curr>** |
| Log entries | <prev> | **<curr>** |

## Next-pass candidates (deferred, not blocking)

<Bulleted list of things this pass identified but did not include as findings:
stubbing low-frequency names, softening paraphrased quotes, etc. Carry the
prior pass's list forward and mark resolved items.>

## Re-run

Run the vault-lint skill again anytime, or weekly on a schedule.
```

## Style notes

- Link every file path so it is clickable in Obsidian, either `[path](path)`
  or the `[[...]]` form when the link resolves cleanly.
- Severity-order findings: Critical first, then Medium, then Low. Inside each
  tier, sort by impact, not by check number.
- Healthy checks belong at the bottom of the findings, not interleaved. They
  are the reassurance section.
- Numbers in the summary table must match the body. Do not say "Medium: 47" up
  top and then list 12 items.
- If a check is genuinely not applicable (e.g., no meetings in scope), say
  "not in scope" rather than fabricating a zero count.
