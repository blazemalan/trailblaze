#!/usr/bin/env python3
"""Ingest pre-flight triage. Run FIRST at every /ingest invocation.

Scans raw/inbox/ + every domain's raw/ dirs and classifies each file BEFORE
any LLM reads it, so empty stubs and duplicates cost zero tokens:

  EMPTY        duration 0:00 / no body text (failed recording, safe to delete)
  JUNK?        <60s or <20 words (mic-test / trivial stub, propose delete)
  DUPLICATE?   a wiki page already exists for its date (confirm before ingest)
  UNPROCESSED  genuinely new, ingest this
  BINARY       non-markdown raw (deck/pdf/doc), file manually if new

A "domain" is any folder (up to two levels deep) containing a wiki/ directory,
e.g. Work/ or Personal/. Run from the vault root (or set VAULT_ROOT).

Usage:  python3 triage.py
"""
import os, re, sys, glob

VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())

# Add filenames here for legacy raw files already absorbed into the wiki that
# should never be flagged (kept empty by default).
LEGACY = set()


def find_domains():
    """A domain = any dir <=2 levels deep containing a wiki/ subdir."""
    out = set()
    for pat in ('*/wiki', '*/*/wiki'):
        for w in glob.glob(os.path.join(VAULT, pat)):
            if os.path.isdir(w):
                rel = os.path.relpath(os.path.dirname(w), VAULT)
                if not rel.startswith('.') and 'archive' not in rel.lower():
                    out.add(rel)
    return sorted(out)


DOMAINS = find_domains()
RAW_GLOBS = ['raw/inbox/*'] + [g for d in DOMAINS for g in (f'{d}/raw/*.md', f'{d}/raw/*/*.md')]
# '{d}' placeholder is filled with a YYYY-MM-DD date at match time (wg.format(d=date))
WIKI_GLOBS = [dom + '/wiki/*/{d}*.md' for dom in DOMAINS]


def frontmatter_and_body(path):
    try:
        text = open(path, encoding='utf-8', errors='replace').read()
    except (OSError, UnicodeError):
        return {}, ''
    fm, body = {}, text
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
                if m:
                    fm[m.group(1).lower()] = m.group(2).strip().strip("'\"")
            body = text[end + 4:]
    return fm, body


try:
    # log.md keeps only recent entries (log-rotate.py); older ones live in log-archive.md.
    # Read both so re-ingest detection still sees archived sources.
    LOG_TEXT = open(os.path.join(VAULT, 'log.md'), encoding='utf-8', errors='replace').read()
    _arch = os.path.join(VAULT, 'log-archive.md')
    if os.path.isfile(_arch):
        LOG_TEXT += open(_arch, encoding='utf-8', errors='replace').read()
except OSError:
    LOG_TEXT = ''


def main():
    if not DOMAINS and not os.path.isdir(os.path.join(VAULT, 'raw')):
        print(f"no vault found at {VAULT} - run from your vault root or set VAULT_ROOT", file=sys.stderr)
        sys.exit(2)
    rows = []
    for g in RAW_GLOBS:
        for path in glob.glob(os.path.join(VAULT, g)):
            base = os.path.basename(path)
            if base in ('.gitkeep', '.DS_Store') or base in LEGACY or os.path.isdir(path):
                continue
            rel = os.path.relpath(path, VAULT)
            if not path.endswith('.md'):
                rows.append(('BINARY', rel, 'non-md raw (deck/pdf/doc), file manually if new'))
                continue
            fm, body = frontmatter_and_body(path)
            # empty stub: 0:00 duration, or no prose outside headers/hr/footer
            # (some pipelines put the whole transcript INSIDE frontmatter, which is not empty)
            prose = [l for l in body.splitlines()
                     if l.strip() and not re.match(r'^(#|---|\*Transcribed|\*\*Duration)', l.strip())]
            yaml_transcript = 'transcript' in open(path, encoding='utf-8', errors='replace').read(3000)
            if fm.get('duration') in ('0:00', '00:00') or (not prose and not yaml_transcript):
                rows.append(('EMPTY', rel, 'failed recording / no content, safe to delete'))
                continue
            # mic-test / trivial stub: short duration or near-no prose (JUNK?)
            dur = fm.get('duration', '')
            m = re.match(r'^(?:(\d+):)?(\d{1,2}):(\d{2})$', dur)
            secs = (int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) if m else None
            words = sum(len(re.findall(r'\w+', l)) for l in prose)
            if not yaml_transcript and ((secs is not None and secs < 60) or words < 20):
                hint = ' (title says test)' if re.search(r'\btest\b', base, re.I) else ''
                rows.append(('JUNK?', rel, f'{dur or "?"} / {words} words, mic-test or trivial stub{hint}, propose delete'))
                continue
            # already processed? same-basename wiki page or a log.md ingest mention.
            # Only for per-domain raw. Inbox is transit, ALWAYS surface what's there.
            in_transit = rel.replace(os.sep, '/').startswith('raw/inbox')
            slug = os.path.splitext(base)[0]
            if not in_transit and (
                    any(glob.glob(os.path.join(VAULT, d, 'wiki', '*', slug + '.md')) or
                        glob.glob(os.path.join(VAULT, d, 'wiki', '*', '*', slug + '.md'))
                        for d in DOMAINS) or
                    slug in LOG_TEXT):
                continue  # processed, stay silent
            date = (re.search(r'(2\d{3}-\d{2}-\d{2})', base) or
                    re.search(r'(2\d{3}-\d{2}-\d{2})', fm.get('date', '')))
            date = date.group(1) if date else None
            dup = None
            if date and in_transit:
                for wg in WIKI_GLOBS:
                    hits = glob.glob(os.path.join(VAULT, wg.format(d=date)))
                    if hits:
                        dup = os.path.relpath(hits[0], VAULT)
                        break
            if dup:
                rows.append(('DUPLICATE?', rel, f'wiki page exists for {date}: {dup}, confirm before ingest'))
            elif in_transit:
                rows.append(('UNPROCESSED', rel, 'inbox transit, triage-move + ingest'))
            else:
                # per-domain raw: unprocessed only if no same-date wiki page exists
                done = False
                if date:
                    for wg in WIKI_GLOBS:
                        if glob.glob(os.path.join(VAULT, wg.format(d=date))):
                            done = True
                            break
                if not done:
                    rows.append(('UNPROCESSED', rel, 'no wiki page for its date, ingest'))

    if not rows:
        print('CLEAN - nothing to ingest')
        return
    w = max(len(r[0]) for r in rows)
    for kind, rel, note in rows:
        print(f'{kind:<{w}}  {rel}  ·  {note}')


if __name__ == '__main__':
    main()
