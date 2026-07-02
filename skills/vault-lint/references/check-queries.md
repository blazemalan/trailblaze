# Vault-Lint Check Queries

Battle-tested one-liners for ad-hoc spot checks. All commands assume the
working directory is the vault root.

> **Note:** most of these checks are automated by `scripts/resolver.py` (run it
> first, see SKILL.md Step 0). Use the patterns below for ad-hoc spot checks
> only.

## Excludes

Paths the lint must never scan:

```
-not -path "*/raw/*" -not -path "*/archive/*" -not -path "*/outputs/*"
-not -path "*/.obsidian/*" -not -path "*/.claude/*" -not -path "*/Templates/*"
-not -path "*/.git/*" -not -path "*/node_modules/*"
```

(Embed inline rather than relying on a shell variable; different shell
sessions will not carry it.)

## Broken wikilinks (check 1)

The resolver covers this fully. For a manual spot check on one link type:

```bash
grep -rn -E '\[\[wiki/people/[^\]|]+' . \
  --include="*.md" \
  --exclude-dir=raw --exclude-dir=archive --exclude-dir=outputs \
  --exclude-dir=.obsidian --exclude-dir=.claude --exclude-dir=Templates \
  | sed -E 's/.*\[\[wiki\/people\/([^]|]+).*/\1/' | sort -u \
  | while read slug; do
      ls */wiki/people/"${slug}.md" */*/wiki/people/"${slug}.md" >/dev/null 2>&1 \
        || echo "MISSING: wiki/people/${slug}.md"
    done
```

Repeat for `concepts`, `decisions`, `projects` by swapping the subfolder.

## Meetings missing `## Source` (check 6)

```bash
find . -path "*/wiki/meetings/*.md" \
  -not -path "*/raw/*" -not -path "*/archive/*" -not -path "*/outputs/*" \
  -exec grep -L "^## Source" {} \;
```

Each path printed is a meeting summary missing its raw-source link or a
"raw not preserved" note.

## Candidate missing entity pages (check 5)

Names mentioned in 2+ meeting files with no entity page. Bare-name wikilinks
first:

```bash
grep -rohE '\[\[[A-Z][a-z]+(\s[A-Z][a-z]+)?\]\]' */wiki/meetings/ */*/wiki/meetings/ 2>/dev/null \
  | sort | uniq -c | sort -rn | head -30
```

Then for each frequent name, check whether an entity page or alias exists:

```bash
NAME="Christine"
grep -rl "aliases:" */wiki/people/ */*/wiki/people/ 2>/dev/null | xargs grep -l "$NAME"
```

If neither a slug file nor an alias entry matches, it is a stub candidate.
Cross-check against any roster/directory page the vault keeps before
recommending; the person may already be listed under a different first name or
full slug.

## Name regression sweep

Terms live in `Reference/lint/watchlist.md` under `## Name regressions` (the
resolver reads them automatically). Manual version:

```bash
for term in "Wrong Spelling One" "Wrong Spelling Two"; do
  echo "=== $term ==="
  grep -rln "$term" . \
    --exclude-dir=raw --exclude-dir=archive --exclude-dir=outputs \
    --exclude-dir=.obsidian --exclude-dir=.claude --exclude-dir=Templates \
    --exclude-dir=.git
done
```

Allow-list: mentions in `log.md`, in a page's own "Name disambiguation" note,
and in `Reference/lint/` itself. Everything else is a finding.

## Orphan pages (check 4)

The resolver covers this (alias-aware). Manual spot check for one page: grep
its slug and each of its aliases across the vault (minus excludes) and count
inbound references from files other than itself and index.md.

## Contradictions and stale claims (checks 2-3)

These are not pure grep tasks; they require reading. Procedure:

1. List the vault's canonical anchors (the user's role/mandate page, current
   priorities, org/roster page, any north-star doc).
2. For each anchor, `grep -rn` the relevant strings across `*/wiki/`.
3. Read the hits and group by claim. Two recent files disagreeing =
   contradiction. Old file overridden by newer = stale.

Helpful probe shapes:

```bash
# Reports-to claims about a person
grep -rn "Jane" */wiki/ | grep -iE "reports? to|under|works for"

# Current priority claims
grep -rn -iE "P1|priority one|top priority" */wiki/
```

## Drift from canonical (check 8)

For each canonical reference doc the vault keeps (voice guide, north stars,
role definition, roster), identify its load-bearing claims (a short list),
then grep the wiki for contradictions. Read each hit in context before
flagging.

## Recap drift on entity/concept pages (check 11)

Living pages should hold durable facts, not meeting logs. Two signals: heading
hits are findings; bullet hits are candidates to read before flagging.

Hard signal (chronological-log headings on `people/` or `concepts/` pages,
zero false positives, flag directly):

```bash
grep -rnE '^#{2,3} +(Past Discussions|Recent Threads|Recent 1:1|Recent 1on1|Chronolog)' \
  */wiki/people/ */wiki/concepts/ */*/wiki/people/ */*/wiki/concepts/ 2>/dev/null
```

Soft signal (`people/` bullets pairing a dated meeting wikilink or an `M/D`
date token with prose). Read each before flagging; durable standing facts that
merely cite a date ("part-time since 5/6") are NOT drift, dated event
narration is:

```bash
grep -rnE '^\s*[-*] .*(\[\[[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}|[^0-9]([0-9]{1,2}/[0-9]{1,2})\b)' \
  */wiki/people/ */*/wiki/people/ 2>/dev/null
```

## Diffing against the prior pass

```bash
ls -1t outputs/vault-lint-*.md | head -2
```

Read the most-recent prior report. Carry forward its deferred-candidates list
and check whether any have been resolved.
