#!/usr/bin/env python3
"""Backlinks lookup. Answers "which pages link to X" in one script run.

Run from the vault root (or set VAULT_ROOT).

Usage:
  python3 backlinks.py jane-doe        # by page slug or bare name/alias
  python3 backlinks.py --dump          # full graph -> stdout JSON

Matches [[target]] / [[target|label]] wikilinks by basename (case-insensitive)
and by frontmatter aliases. Replaces vault-wide greps for the most common
query shape ("which meetings involve <person>").
"""
import os, re, sys, json
from collections import defaultdict

VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())
SKIP_DIRS = {'.git', '.obsidian', '.claude', '.auto-memory', '.trash', 'node_modules',
             'archive', 'outputs', 'Templates'}
LINK = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]')


def md_files():
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith('.md'):
                yield os.path.join(root, f)


def aliases_of(path):
    out = []
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            head = fh.read(2000)
    except OSError:
        return out
    m = re.search(r'^aliases:\s*\n((?:\s*- .+\n)+)', head, re.M)
    if m:
        out = [re.sub(r'^\s*- ', '', l).strip().strip('"\'') for l in m.group(1).splitlines() if l.strip()]
    return out


def main():
    # alias/basename -> canonical rel path
    name_to_page = {}
    pages = list(md_files())
    for p in pages:
        rel = os.path.relpath(p, VAULT)
        base = os.path.splitext(os.path.basename(p))[0].lower()
        name_to_page.setdefault(base, rel)
        for a in aliases_of(p):
            name_to_page.setdefault(a.lower(), rel)

    graph = defaultdict(set)
    for p in pages:
        rel = os.path.relpath(p, VAULT)
        try:
            text = open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for target in LINK.findall(text):
            t = target.strip().lower()
            resolved = name_to_page.get(os.path.basename(t)) or name_to_page.get(t)
            if resolved and resolved != rel:
                graph[resolved].add(rel)

    if len(sys.argv) > 1 and sys.argv[1] == '--dump':
        print(json.dumps({k: sorted(v) for k, v in graph.items()}, indent=1))
        return
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    q = sys.argv[1].lower()
    target = name_to_page.get(q) or name_to_page.get(os.path.basename(q))
    if not target:
        print(f"no page found for '{sys.argv[1]}'"); sys.exit(1)
    try:
        print(f"# inbound links -> {target}")
        for src in sorted(graph.get(target, [])):
            print(src)
    except BrokenPipeError:  # piped to head, fine
        sys.stderr.close()


if __name__ == '__main__':
    main()
