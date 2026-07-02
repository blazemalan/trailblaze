#!/usr/bin/env python3
"""Generate per-domain wiki/index.md from page frontmatter.

The index is a COMPLETE catalog of every wiki page, one line each, grouped by
section. The one-liner is the page's `description:` frontmatter (fallback: H1).
Run this on every ingest instead of hand-editing index.md; the index can then
never drift or be forgotten.

A "domain" is any folder (up to two levels deep) containing a wiki/ directory,
e.g. Work/ or Personal/. Standard sections (sources, people, concepts,
decisions, projects, meetings) come first; any extra folders under wiki/
(topic folders like Journal/ or Health/) are appended automatically.

Run from the vault root (or set VAULT_ROOT).

Usage:
  gen-index.py --emit <domain>      # print regenerated index to stdout (no write)
  gen-index.py --check [domain]     # exit 1 if any committed index != regenerated
  gen-index.py --write [domain]     # overwrite the index.md file(s)
  gen-index.py [domain]             # default: unified-ish diff to stdout, no write

  <domain> = a domain folder name (e.g. work | personal) or all   (default: all)

Stdlib only. Deterministic output (no timestamps) so --check is stable.
"""
import os, re, sys, glob, difflib

VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())

# Files that are never indexed (housekeeping / gitignored secrets), not a content choice.
HARD_SKIP = {'secrets.local.md', '.gitkeep', 'index.md'}

SRC_BQ = ("Source pages are for non-meeting raw (articles, decks, emails). "
          "Meeting transcripts are summarized directly in `wiki/meetings/` - no separate source page.")
PROJ_BQ = "Every project file, grouped by project folder. Generated - holds everything under `projects/`."

# Section = (Title, folder-under-wiki-root, ordering, link_style, blockquote|None)
#   ordering   : alpha | date_asc | date_desc | projects
#   link_style : bare (bare unless basename collides) | path (always path-qualified)
STANDARD_SECTIONS = [
    ('Sources',   'sources',   'date_desc', 'bare', SRC_BQ),
    ('People',    'people',    'alpha',     'bare', None),
    ('Concepts',  'concepts',  'alpha',     'bare', None),
    ('Decisions', 'decisions', 'date_desc', 'bare', None),
    ('Projects',  'projects',  'projects',  'path', PROJ_BQ),
    ('Meetings',  'meetings',  'date_asc',  'path', None),
]
STANDARD_NAMES = {s[1] for s in STANDARD_SECTIONS}

DATE_RE = re.compile(r'(2\d{3}-\d{2}-\d{2})')
YM_RE = re.compile(r'(2\d{3}-\d{2})(?!-\d)')  # year-month with no day (e.g. 2026-05-company-all-hands)
H1_RE = re.compile(r'^# (.+)$', re.M)


def find_domain_dirs():
    """A domain = any dir <=2 levels deep containing a wiki/ subdir."""
    out = set()
    for pat in ('*/wiki', '*/*/wiki'):
        for w in glob.glob(os.path.join(VAULT, pat)):
            if os.path.isdir(w):
                rel = os.path.relpath(os.path.dirname(w), VAULT)
                if not rel.startswith('.') and 'archive' not in rel.lower():
                    out.add(rel)
    return sorted(out)


def build_domains():
    """cli-key -> domain config. Key = domain folder name lowercased (full
    relative path as fallback when two domains share a folder name)."""
    out = {}
    for rel in find_domain_dirs():
        label = os.path.basename(rel)
        wiki_rel = os.path.join(rel, 'wiki').replace(os.sep, '/')
        sections = list(STANDARD_SECTIONS)
        base = os.path.join(VAULT, wiki_rel)
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if (os.path.isdir(p) and name not in STANDARD_NAMES
                    and name.lower() != 'archive' and not name.startswith('.')):
                files = [f for f in os.listdir(p) if f.endswith('.md') and f not in HARD_SKIP]
                dated = [f for f in files if DATE_RE.search(f)]
                ordering = 'date_asc' if files and len(dated) >= len(files) / 2 else 'alpha'
                sections.append((name, name, ordering, 'bare', None))
        cfg = {'root': wiki_rel, 'title': f'{label} Wiki — Index', 'sections': sections}
        key = label.lower()
        out[key if key not in out else rel.replace(os.sep, '/').lower()] = cfg
    return out


def parse_page(path):
    """Return (fm_dict, list_items, body, h1_text)."""
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError:
        return {}, [], '', ''
    fm, items, body = {}, [], text
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
                if m:
                    fm[m.group(1).lower()] = m.group(2)
                elif line.strip().startswith('- '):
                    items.append(line.strip()[2:].strip('"\''))
            body = text[end + 4:]
    h1 = H1_RE.search(body)
    return fm, items, body, (h1.group(1).strip() if h1 else '')


def one_liner(path):
    fm, _items, body, h1 = parse_page(path)
    desc = fm.get('description', '').strip().strip('"\'').strip()
    if desc:
        return desc
    # fallback: prefer the H1 title over a random body line; only use a body line
    # if there's no H1. Skip headings/blockquotes/list-markers/tables/rules.
    if h1:
        return h1
    for line in body.splitlines():
        s = line.strip()
        if not s or s[0] in '#>-*|' or s.startswith('---') or re.match(r'^\d+\.', s):
            continue
        return s
    return os.path.splitext(os.path.basename(path))[0]


def slug_of(path):
    return os.path.splitext(os.path.basename(path))[0]


def date_key(path):
    s = slug_of(path)
    m = DATE_RE.search(s)
    if m:
        return m.group(1)
    m = YM_RE.search(s)               # no-day month label sorts at month start
    return m.group(1) + '-00' if m else ''


def build_collisions():
    """Basenames that appear more than once anywhere in the vault (incl. raw);
    those must be path-qualified so wikilinks stay unambiguous."""
    counts = {}
    skip = {'.git', '.obsidian', '.trash', 'node_modules', '.auto-memory'}
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith('.md'):
                b = f[:-3].lower()
                counts[b] = counts.get(b, 0) + 1
    return {b for b, c in counts.items() if c > 1}


def section_files(domain_root, folder):
    base = os.path.join(VAULT, domain_root, folder)
    out = []
    if not os.path.isdir(base):
        return out
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {'.git', 'archive'}]
        for f in files:
            if f.endswith('.md') and f not in HARD_SKIP:
                out.append(os.path.join(root, f))
    return out


def entry_line(domain_root, path, link_style, collisions):
    slug = slug_of(path)
    domain_dir = os.path.dirname(domain_root)
    rel_to_domain = os.path.relpath(path, os.path.join(VAULT, domain_dir))[:-3]
    # nested = file is in a subfolder below the section root (e.g. projects/<x>/file)
    rel_in_wiki = os.path.relpath(path, os.path.join(VAULT, domain_root))
    nested = rel_in_wiki.count(os.sep) >= 2  # <section>/<sub>/file.md
    qualify = link_style == 'path' or nested or slug.lower() in collisions
    target = rel_to_domain.replace(os.sep, '/') if qualify else slug
    return f"- [[{target}|{slug}]] — {one_liner(path)}"


def order_files(files, ordering):
    if ordering == 'alpha':
        return sorted(files, key=lambda p: slug_of(p).lower())
    if ordering in ('date_asc', 'date_desc'):
        dated = sorted([p for p in files if date_key(p)], key=date_key, reverse=(ordering == 'date_desc'))
        undated = sorted([p for p in files if not date_key(p)], key=lambda p: slug_of(p).lower())
        return dated + undated
    return sorted(files, key=lambda p: slug_of(p).lower())


def render_projects(domain_root, files, collisions):
    """Projects: standalone files (alpha) first, then one ### group per subfolder."""
    proj_root = os.path.join(VAULT, domain_root, 'projects')
    standalone, groups = [], {}
    for p in files:
        rel = os.path.relpath(p, proj_root)
        if os.sep in rel:
            groups.setdefault(rel.split(os.sep, 1)[0], []).append(p)
        else:
            standalone.append(p)
    lines = []
    for p in sorted(standalone, key=lambda p: slug_of(p).lower()):
        lines.append(entry_line(domain_root, p, 'path', collisions))
    for folder in sorted(groups):
        lines.append('')
        lines.append(f"### {folder}/")
        for p in sorted(groups[folder], key=lambda p: os.path.relpath(p, proj_root).lower()):
            lines.append(entry_line(domain_root, p, 'path', collisions))
    return lines


def render_domain(cfg, collisions):
    root = cfg['root']
    out = []
    out.append('<!-- GENERATED by gen-index.py — do not hand-edit; add a `description:` to the page and re-run the script -->')
    out.append('')
    out.append(f"# {cfg['title']}")
    out.append('')
    out.append("Complete catalog of every wiki page in this domain, "
               "generated from each page's `description:` frontmatter. Do not hand-edit.")
    out.append('')

    for title, folder, ordering, link_style, bq in cfg['sections']:
        files = section_files(root, folder)
        n = len(files)
        out.append(f"## {title} ({n})")
        out.append('')
        if bq:
            out.append(f"> {bq}")
            out.append('')
        if n == 0:
            out.append('_(empty)_')
            out.append('')
            continue
        if ordering == 'projects':
            out += render_projects(root, files, collisions)
            out.append('')
        else:
            for p in order_files(files, ordering):
                out.append(entry_line(root, p, link_style, collisions))
            out.append('')
    # normalize: single trailing newline
    return '\n'.join(out).rstrip() + '\n'


def main():
    domains_cfg = build_domains()
    if not domains_cfg:
        print(f"no domains found under {VAULT} (a domain is a folder containing wiki/) - "
              "run from your vault root or set VAULT_ROOT", file=sys.stderr)
        sys.exit(2)

    args = sys.argv[1:]
    mode = 'diff'
    for flag in ('--emit', '--check', '--write'):
        if flag in args:
            mode = flag[2:]
            args.remove(flag)
    target = (args[0].lower() if args else 'all')
    domains = list(domains_cfg) if target == 'all' else [target]
    if target != 'all' and target not in domains_cfg:
        print(f"unknown domain '{target}' - use: {' | '.join(sorted(domains_cfg))} | all", file=sys.stderr)
        sys.exit(2)

    collisions = build_collisions()
    stale = []
    for dom in domains:
        cfg = domains_cfg[dom]
        new = render_domain(cfg, collisions)
        path = os.path.join(VAULT, cfg['root'], 'index.md')
        old = ''
        if os.path.isfile(path):
            with open(path, encoding='utf-8', errors='replace') as fh:
                old = fh.read()
        if mode == 'emit':
            sys.stdout.write(new)
        elif mode == 'write':
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(new)
            print(f"wrote {os.path.relpath(path, VAULT)} ({new.count(chr(10))} lines)")
        elif mode == 'check':
            if old != new:
                stale.append(dom)
        else:  # diff
            if old == new:
                print(f"# {dom}: index up to date")
            else:
                d = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                         fromfile=f"{dom}/index.md (committed)", tofile=f"{dom}/index.md (regenerated)")
                sys.stdout.writelines(d)
    if mode == 'check':
        if stale:
            print("STALE index (run gen-index.py --write): " + ", ".join(stale))
            sys.exit(1)
        print("all indexes current")


if __name__ == '__main__':
    main()
