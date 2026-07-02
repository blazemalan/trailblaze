#!/usr/bin/env python3
"""Keep log.md lean: retain the most recent N entries, move older ones to
log-archive.md. Entries are chronological (most recent at the BOTTOM). Idempotent,
safe to run on every ingest. Archived entries stay grep-able and triage.py reads
both files, so dedup/recency detection still works.

Run from the vault root (or set VAULT_ROOT).

Usage: log-rotate.py [N]      (default 60)
"""
import os, re, sys

VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
LOG = os.path.join(VAULT, 'log.md')
ARCH = os.path.join(VAULT, 'log-archive.md')
ENTRY = r'(?m)(?=^## \[2\d{3}-)'   # real dated entries start with "## [2###-"; a template "## [YYYY-" stays in the header

ARCH_HEADER = ("# Vault Log - Archive\n\n"
               "Older entries rotated out of `log.md` by `log-rotate.py` (chronological, most recent at the bottom). "
               "Still grep-able; `triage.py` reads this file too, so re-ingest detection is unaffected.\n")


def split_entries(text):
    m = re.search(r'^## \[2\d{3}-', text, re.M)
    if not m:
        return text, []
    header, body = text[:m.start()], text[m.start():]
    entries = [p for p in re.split(ENTRY, body) if p.strip()]
    return header, entries


def main():
    if not os.path.isfile(LOG):
        print(f"no log.md at {VAULT} - run from your vault root or set VAULT_ROOT", file=sys.stderr)
        sys.exit(2)
    text = open(LOG, encoding='utf-8').read()
    header, entries = split_entries(text)
    if len(entries) <= N:
        print(f"{len(entries)} entries <= {N}; no rotation needed")
        return
    keep, rotate = entries[-N:], entries[:-N]

    # existing archive entries (chronological) + newly rotated (newer) -> still chronological
    prev = []
    if os.path.isfile(ARCH):
        _, prev = split_entries(open(ARCH, encoding='utf-8').read())
    with open(ARCH, 'w', encoding='utf-8') as fh:
        fh.write(ARCH_HEADER + '\n' + ''.join(prev) + ''.join(rotate).rstrip() + '\n')
    with open(LOG, 'w', encoding='utf-8') as fh:
        fh.write(header.rstrip() + '\n\n' + ''.join(keep).rstrip() + '\n')

    print(f"rotated {len(rotate)} entries -> log-archive.md; kept {len(keep)} in log.md")


if __name__ == '__main__':
    main()
