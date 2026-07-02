#!/usr/bin/env python3
"""Insert or replace the single-line `description:` frontmatter field on a page.

Deterministic tooling so agents never hand-edit YAML. Reads the description text
from an argument or a file (avoids shell quoting issues).

Run from the vault root (or set VAULT_ROOT for --json relative paths).

Usage:
  set-description.py <page.md> --text "one-liner"
  set-description.py <page.md> --from <textfile>
  set-description.py <page.md> --json <sidecar.json>   # {"path":..,"description":..}
"""
import sys, re, json, os


def set_desc(path, desc):
    desc = ' '.join(desc.replace('"', "'").split()).strip()
    line = f'description: "{desc}"'
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    crlf = '\r\n' in text[:300]           # preserve the file's line-ending style
    work = text.replace('\r\n', '\n')     # normalize for editing (CRLF-safe)
    m = re.match(r'\A---\n(.*?)\n---', work, re.S)
    if m:
        out, placed = [], False
        for l in m.group(1).split('\n'):
            if re.match(r'^description\s*:', l):
                if not placed:            # replace the first description, drop any duplicates
                    out.append(line); placed = True
                continue
            out.append(l)
        if not placed:
            out.insert(0, line)           # insert if the page had none
        new = '---\n' + '\n'.join(out) + work[m.end(1):]   # m.end(1) = before the closing '\n---'
    else:
        new = f'---\n{line}\n---\n\n' + work   # no frontmatter block, create one
    if crlf:
        new = new.replace('\n', '\r\n')
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(new)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    if a[0] == '--json':
        d = json.load(open(a[1], encoding='utf-8'))
        set_desc(d['path'] if os.path.isabs(d['path']) else os.path.join(
            os.environ.get('VAULT_ROOT', '.'), d['path']), d['description'])
        return
    path = a[0]
    if '--text' in a:
        desc = a[a.index('--text') + 1]
    elif '--from' in a:
        desc = open(a[a.index('--from') + 1], encoding='utf-8').read()
    else:
        print(__doc__); sys.exit(1)
    set_desc(path, desc)
    print(f'set description on {path}')


if __name__ == '__main__':
    main()
