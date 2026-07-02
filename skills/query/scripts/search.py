#!/usr/bin/env python3
"""Deterministic wiki search. Run BEFORE any agent fan-out.

Scores every wiki/schema page against query terms using filename, H1,
frontmatter (aliases/description/tags), and capped full-text hits.
Returns the top-N paths; the LLM then reads only those files.

Run from the vault root (or set VAULT_ROOT).

Usage:
  python3 search.py <term> [term ...] [-n 8] [--json]

Scoring per term: filename hit 5 · H1/title 4 · alias 4 · description 3 ·
tag 2 · body hits 1 each (capped at 5). Multi-term queries sum scores;
pages matching more distinct terms rank higher (coverage bonus).
"""
import os, re, sys, json

VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())
SKIP_DIRS = {'.git', '.obsidian', '.claude', '.auto-memory', '.trash', 'node_modules',
             'raw', 'archive', 'outputs', 'Templates'}


def walk():
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith('.md'):
                yield os.path.join(root, f)


def parse(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError:
        return None
    fm = {}
    body = text
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
                if m:
                    fm[m.group(1).lower()] = m.group(2)
                elif line.strip().startswith('- '):
                    fm.setdefault('_list', []).append(line.strip()[2:].strip('"\''))
            body = text[end + 4:]
    h1 = re.search(r'^# (.+)$', body, re.M)
    return {
        'name': os.path.splitext(os.path.basename(path))[0].lower(),
        'h1': (h1.group(1) if h1 else '').lower(),
        'desc': fm.get('description', '').lower(),
        'tags': fm.get('tags', '').lower() + ' ' + ' '.join(fm.get('_list', [])).lower(),
        'aliases': fm.get('aliases', '').lower() + ' ' + ' '.join(fm.get('_list', [])).lower(),
        'body': body.lower(),
    }


def main():
    args = [a for a in sys.argv[1:]]
    n = 8
    if '-n' in args:
        i = args.index('-n')
        n = int(args[i + 1]); del args[i:i + 2]
    use_json = False
    if '--json' in args:
        i = args.index('--json')
        use_json = True; del args[i:i + 1]
    terms = [t.lower() for t in args if t.strip()]
    if not terms:
        print(__doc__); sys.exit(1)

    results = []
    for path in walk():
        p = parse(path)
        if not p:
            continue
        score, matched = 0, 0
        for t in terms:
            s = 0
            if t in p['name']: s += 5
            if t in p['h1']: s += 4
            if t in p['aliases']: s += 4
            if t in p['desc']: s += 3
            if t in p['tags']: s += 2
            s += min(p['body'].count(t), 5)
            if s:
                matched += 1
            score += s
        if score:
            results.append((score * (1 + matched - 1), os.path.relpath(path, VAULT)))
    results.sort(key=lambda r: -r[0])
    if use_json:
        print(json.dumps([{"score": r[0], "path": r[1]} for r in results[:n]], indent=1))
    else:
        for score, rel in results[:n]:
            print(f"{score:4d}  {rel}")
        if not results:
            print("no hits - fall back to index.md scan or agent search")


if __name__ == '__main__':
    main()
