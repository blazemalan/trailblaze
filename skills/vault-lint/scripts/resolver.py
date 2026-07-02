#!/usr/bin/env python3
"""Deterministic vault-lint resolver: checks 1 (broken wikilinks), 4 (orphans),
6 (meeting Source), 7 (stale inbox), 9 (CLAUDE.md size/placement), 10 (index
staleness + description coverage) + name-regression sweep + recap-drift hard
signal + file counts.

A "domain" is any folder (up to two levels deep) containing a wiki/ directory.
Name-regression terms are read from `Reference/lint/watchlist.md` (bullets under
a `## Name regressions` heading), if that file exists.

Run from the vault root (or set VAULT_ROOT).

Usage:
  python3 resolver.py /tmp/vault-lint-resolver.json
"""
import os, re, json, glob, subprocess, sys
from datetime import datetime, timezone

if len(sys.argv) < 2:
    print(__doc__.strip(), file=sys.stderr)
    sys.exit(1)

VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())
if not (os.path.isfile(os.path.join(VAULT, 'CLAUDE.md')) or os.path.isfile(os.path.join(VAULT, 'log.md'))):
    print(f"no vault found at {VAULT} (no CLAUDE.md or log.md) - run from your vault root or set VAULT_ROOT",
          file=sys.stderr)
    sys.exit(2)

HIDDEN = {'.git', '.obsidian', '.claude', '.agents', '.auto-memory', '.trash', 'node_modules'}


def find_domains():
    out = set()
    for pat in ('*/wiki', '*/*/wiki'):
        for w in glob.glob(os.path.join(VAULT, pat)):
            if os.path.isdir(w):
                rel = os.path.relpath(os.path.dirname(w), VAULT)
                if not rel.startswith('.') and 'archive' not in rel.lower():
                    out.add(rel.replace(os.sep, '/'))
    return sorted(out)


DOMAINS = find_domains()


def walk_files():
    out = []
    for root, dirs, files in os.walk(VAULT):
        rel = os.path.relpath(root, VAULT)
        dirs[:] = [d for d in dirs if d not in HIDDEN and not d.startswith('.')]
        for f in files:
            if f == '.DS_Store': continue
            out.append(os.path.normpath(os.path.join(rel, f)) if rel != '.' else f)
    return out

ALL_FILES = walk_files()
MD_FILES = [f for f in ALL_FILES if f.endswith('.md')]

# --- file cache --------------------------------------------------------------
_file_cache = {}
def read_file(rel):
    if rel not in _file_cache:
        with open(os.path.join(VAULT, rel), encoding='utf-8', errors='replace') as f:
            _file_cache[rel] = f.read()
    return _file_cache[rel]

def is_scan_source(rel):
    """Lint scope for link SOURCES: wiki+schema layers only."""
    parts = rel.split(os.sep)
    if any(p in ('raw', 'archive', 'outputs', 'Templates') for p in parts): return False
    return True

# --- target maps -------------------------------------------------------------
by_relpath = {}      # lowercase relpath (with ext) -> relpath
by_basename = {}     # lowercase basename (no .md) -> [relpaths]
by_alias = {}        # lowercase alias -> [relpaths]

for f in ALL_FILES:
    by_relpath[f.lower()] = f
for f in MD_FILES:
    base = os.path.basename(f)[:-3].lower()
    by_basename.setdefault(base, []).append(f)
# non-md attachments resolvable by basename too (Obsidian embeds)
for f in ALL_FILES:
    if not f.endswith('.md'):
        by_basename.setdefault(os.path.basename(f).lower(), []).append(f)

FM_RE = re.compile(r'\A---\n(.*?)\n---', re.S)
def aliases_of(rel):
    try:
        text = read_file(rel)
    except OSError:
        return []
    m = FM_RE.match(text)
    if not m: return []
    fm, out, in_al = m.group(1), [], False
    for line in fm.split('\n'):
        if re.match(r'^aliases\s*:\s*$', line): in_al = True; continue
        if re.match(r'^aliases\s*:\s*\[(.*)\]', line):
            inner = re.match(r'^aliases\s*:\s*\[(.*)\]', line).group(1)
            out += [a.strip().strip('"\'') for a in inner.split(',') if a.strip()]
            continue
        if in_al:
            mm = re.match(r'^\s+-\s+(.+?)\s*$', line)
            if mm: out.append(mm.group(1).strip().strip('"\''))
            elif line.strip() and not line.startswith(' '): in_al = False
    return out

for f in MD_FILES:
    for a in aliases_of(f):
        by_alias.setdefault(a.lower(), []).append(f)

# --- link extraction ----------------------------------------------------------
FENCE_RE = re.compile(r'^(```|~~~)')
CODESPAN_RE = re.compile(r'`[^`\n]*`')
LINK_RE = re.compile(r'!?\[\[([^\[\]\n]+?)\]\]')

def resolve(target):
    """Return (resolved_relpath_or_None, method)."""
    t = target.strip()
    if t.startswith('#'): return ('SELF', 'heading')
    if '\\|' in t: t = t.split('\\|')[0]
    elif '|' in t: t = t.split('|')[0]
    t = t.split('#')[0].strip().strip('/')
    if not t: return ('SELF', 'heading')
    tl = t.lower()
    for cand in (tl, tl + '.md'):
        if cand in by_relpath: return (by_relpath[cand], 'path')
    base = tl.split('/')[-1]
    if base in by_basename: return (by_basename[base][0], 'basename')
    if base.endswith('.md') and base[:-3] in by_basename: return (by_basename[base[:-3]][0], 'basename')
    if tl in by_alias: return (by_alias[tl][0], 'alias')
    return (None, 'unresolved')

broken, inbound = [], {}
links_total = 0
for f in MD_FILES:
    if not is_scan_source(f): continue
    try:
        lines = read_file(f).split('\n')
    except OSError:
        continue
    in_fence = False
    for i, line in enumerate(lines, 1):
        if FENCE_RE.match(line.strip()): in_fence = not in_fence; continue
        if in_fence: continue
        clean = CODESPAN_RE.sub('', line)
        for m in LINK_RE.finditer(clean):
            links_total += 1
            tgt, how = resolve(m.group(1))
            if tgt is None:
                broken.append({'file': f, 'line': i, 'link': m.group(1)[:120]})
            elif tgt != 'SELF' and os.path.basename(f) != 'index.md':
                # index.md is GENERATED and links every page, so it can't count as a
                # real inbound link, else the orphan check (4) would always read zero.
                # (Broken-link detection above still runs on index.md.)
                inbound.setdefault(tgt, set()).add(f)

# --- check 4: orphans (wiki pages, zero inbound from other files) -------------
orphans = []
for f in MD_FILES:
    if '/wiki/' not in '/' + f.replace(os.sep, '/'): continue
    if os.path.basename(f) == 'index.md': continue
    src = inbound.get(f, set()) - {f}
    if not src: orphans.append(f)

# --- check 6: meeting summaries missing ## Source -------------------------------
missing_source = []
for f in MD_FILES:
    p = '/' + f.replace(os.sep, '/')
    if '/wiki/meetings/' in p and is_scan_source(f):
        if os.path.basename(f) == 'index.md': continue
        text = read_file(f)
        if not re.search(r'^##+ Source', text, re.M) and 'raw not preserved' not in text:
            missing_source.append(f)

# --- check 7: stale inbox (git age when available, file mtime fallback) --------
inbox = []
ib_dir = os.path.join(VAULT, 'raw', 'inbox')
if os.path.isdir(ib_dir):
    now = datetime.now(timezone.utc)
    for f in sorted(os.listdir(ib_dir)):
        if f in ('.gitkeep', '.DS_Store'): continue
        rel = os.path.join('raw/inbox', f)
        try:
            d = subprocess.run(['git', 'log', '-1', '--format=%aI', '--', rel],
                               cwd=VAULT, capture_output=True, text=True).stdout.strip()
        except Exception:
            d = ''
        age = None
        if d:
            age = (now - datetime.fromisoformat(d)).days
            basis = 'git'
        else:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(VAULT, rel)), tz=timezone.utc)
                age = (now - mtime).days
                basis = 'mtime'
            except OSError:
                basis = 'unknown'
        inbox.append({'file': rel, 'age_days': age, 'basis': basis})

# --- check 9: CLAUDE.md cascade -------------------------------------------------
claude_md = []
for f in MD_FILES:
    if os.path.basename(f) == 'CLAUDE.md':
        n = len(read_file(f).splitlines())
        claude_md.append({'file': f, 'lines': n})

# --- check 10: index staleness + description coverage ----------------------------
# index.md files are GENERATED from each page's `description:` frontmatter by
# the ingest skill's gen-index.py. Flag: (a) any committed index that differs
# from a fresh regen ("stale, run gen-index.py --write"); and (b) indexed pages
# with no `description:` one-liner (they degrade to an H1 fallback).
index_report = {}
GEN = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', 'ingest', 'scripts', 'gen-index.py'))
if os.path.isfile(GEN):
    try:
        env = dict(os.environ, VAULT_ROOT=VAULT)
        r = subprocess.run([sys.executable, GEN, '--check', 'all'],
                           cwd=VAULT, env=env, capture_output=True, text=True, timeout=90)
        index_report['stale_exit'] = r.returncode  # 0 = all current, 1 = stale
        index_report['stale'] = (r.stdout.strip().splitlines() or [r.stderr.strip()])[-1]
    except Exception as e:
        index_report['stale'], index_report['stale_exit'] = f'gen-index --check failed: {e}', -1
else:
    index_report['stale'], index_report['stale_exit'] = f'gen-index.py not found at {GEN}', -1

def _has_desc(rel):
    try:
        m = FM_RE.match(read_file(rel))
    except OSError:
        return False
    return bool(m and re.search(r'^description\s*:', m.group(1), re.M))

missing_desc = []
for dom in DOMAINS:
    wiki = os.path.join(VAULT, dom, 'wiki')
    if not os.path.isdir(wiki): continue
    for sub in sorted(os.listdir(wiki)):
        d = os.path.join(wiki, sub)
        if not os.path.isdir(d) or sub.startswith('.'): continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != 'archive']
            for fn in files:
                if fn.endswith('.md') and fn not in ('index.md', 'secrets.local.md'):
                    rel = os.path.relpath(os.path.join(root, fn), VAULT)
                    if not _has_desc(rel):
                        missing_desc.append(rel)
index_report['pages_missing_description'] = sorted(missing_desc)
index_report['missing_description_count'] = len(missing_desc)

# --- name regression sweep ------------------------------------------------------
# Terms come from Reference/lint/watchlist.md, bullets under "## Name regressions".
def watch_terms():
    p = os.path.join(VAULT, 'Reference', 'lint', 'watchlist.md')
    if not os.path.isfile(p): return []
    text = open(p, encoding='utf-8', errors='replace').read()
    m = re.search(r'^##\s+Name regressions\s*\n(.*?)(?=^##\s|\Z)', text, re.M | re.S)
    if not m: return []
    terms = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if s.startswith('- '):
            terms.append(s[2:].split(' (')[0].strip().strip('`').strip())
    return [t for t in terms if t]

regressions = {}
WATCHLIST_REL = os.path.join('Reference', 'lint', 'watchlist.md')
for term in watch_terms():
    hits = []
    for f in MD_FILES:
        if not is_scan_source(f) or f in ('log.md', 'log-archive.md') or f == WATCHLIST_REL: continue
        text = read_file(f)
        if term in text: hits.append(f)
    if hits: regressions[term] = hits

# --- recap drift hard signal ---------------------------------------------------
recap_hard = []
H_RE = re.compile(r'^#{2,3} +(Past Discussions|Recent Threads|Recent 1:1|Recent 1on1|Chronolog)', re.M)
for f in MD_FILES:
    p = '/' + f.replace(os.sep, '/')
    if ('/wiki/people/' in p or '/wiki/concepts/' in p) and is_scan_source(f):
        text = read_file(f)
        for m in H_RE.finditer(text):
            recap_hard.append({'file': f, 'heading': m.group(0).strip()})

# --- counts ----------------------------------------------------------------------
counts = {}
for dom in DOMAINS:
    label = os.path.basename(dom)
    wiki = os.path.join(VAULT, dom, 'wiki')
    if not os.path.isdir(wiki): continue
    for sub in sorted(os.listdir(wiki)):
        if not os.path.isdir(os.path.join(wiki, sub)) or sub.startswith('.'): continue
        prefix = os.path.normpath(os.path.join(dom, 'wiki', sub)) + os.sep
        counts[f'{label} {sub}'] = len([f for f in MD_FILES if f.startswith(prefix)])
try:
    counts['log entries'] = len(re.findall(r'^## \[', read_file('log.md'), re.M))
except OSError:
    counts['log entries'] = 0
counts['md files total'] = len(MD_FILES)
counts['links scanned'] = links_total

# basename collisions (info)
collisions = {b: fs for b, fs in by_basename.items()
              if len([x for x in fs if x.endswith('.md')]) > 1 and not b.startswith('index')}

out = {'domains': DOMAINS,
       'broken_links': broken, 'orphans': orphans, 'missing_source': missing_source,
       'inbox': inbox, 'claude_md': claude_md, 'index_report': index_report,
       'name_regressions': regressions, 'recap_hard': recap_hard,
       'counts': counts,
       'collisions': {k: v for k, v in sorted(collisions.items()) if len(v) > 1}}
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print(f"broken={len(broken)} orphans={len(orphans)} missing_source={len(missing_source)} "
      f"inbox={len(inbox)} regressions={sum(len(v) for v in regressions.values())} "
      f"recap_hard={len(recap_hard)} collisions={len([k for k,v in collisions.items() if len(v)>1])} "
      f"index_stale={index_report.get('stale_exit')} pages_missing_desc={index_report.get('missing_description_count')}")
print(json.dumps(counts, indent=1))
print(json.dumps([c for c in claude_md], indent=1))
