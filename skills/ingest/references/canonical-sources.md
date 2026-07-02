# Canonical sources: read these BEFORE stubbing new entities

Before creating a new `wiki/people/<slug>.md` or `wiki/concepts/<slug>.md`
page, verify the name/concept against the vault's canonical sources. Getting it
right the first time is cheaper than fixing a misspelling after it propagates
across five meeting pages.

## For people

| Source | What it has | When to check |
|---|---|---|
| Existing `wiki/people/*.md` pages (all domains) | Pages + `aliases:` lists | Always, before stubbing. The person may already exist under a different slug |
| Any directory/roster page the vault keeps (e.g. `Reference/people-directory.md`, an org chart page) | Titles, roles, spelling | Whenever the vault has one |
| A glossary page, if the vault keeps one | Known transcription-misheard variants of names | When a transcript spelling looks off |
| Connected tools (workspace directory, email, chat), if available | Live display names and handles | When the name is not in any of the above |

If a name is in the transcript but not in any canonical source, and no
connected tool can confirm it, ask the user before stubbing. Inventing a stub
for a misheard or misattributed name is worse than asking once.

## For concepts / programs / projects

Grep the wiki for any near-match slug before creating a new page. Naming
collisions and near-duplicates are the most common defect in wiki maintenance.
Check `wiki/concepts/`, `wiki/projects/`, and `Reference/` first.

## For decisions

`<Domain>/wiki/decisions/`, naming convention `YYYY-MM-decision-slug.md`.
Browse recent entries before writing a new one in case the same decision is
already filed under a different month.

## When the canonical source disagrees with the transcript

Trust the canonical source. Transcripts have typos and diarization errors;
canonical wiki pages have been reconciled. If the disagreement is meaningful
(role changed, person left), flag it in your report back to the user. That
might be the actual signal in the ingest, and the canonical source needs
updating.

Reconcile, do not silently follow: if a transcript casually contradicts a
canonical source, surface the conflict rather than just writing down what the
transcript said.
