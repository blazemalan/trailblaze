#!/usr/bin/env python3
"""Build graph.json for The Grid from an Obsidian-style Markdown vault.

Nodes = markdown notes, links = wikilinks. Bare-name [[Links]] resolve via
filename stem first, then frontmatter aliases. Unresolved links are dropped
(no ghost nodes in v1).

Vault path comes from the grid config; output is written to the state dir.
Pass --vault <path> to override the configured vault for a one-off build.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

from _config import SETUP_HINT, graph_path, load_config, vault_path

VAULT: Path | None = None  # resolved in main() from config or --vault
SKIP_DIRS = {".obsidian", ".claude", ".git", "node_modules"}
# Notes that are plumbing, not knowledge. A rotated activity/log-archive note
# wikilinks to nearly everything it ever mentioned (degree ~135), so it renders
# as a giant dead planet that drags the whole layout. The file itself is a
# legitimate vault artifact; only the graph skips it.
SKIP_NOTES = {"log-archive"}

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ALIASES_LINE = re.compile(r"^aliases:\s*\[(.*)\]\s*$")
ALIAS_ITEM = re.compile(r"^\s*-\s+(.+?)\s*$")


def note_id(p: Path) -> str:
    return str(p.relative_to(VAULT)).removesuffix(".md")


def last_edit_epochs() -> dict[str, float]:
    """Last-commit time per path. Clone mtimes lie; git history doesn't.

    On a non-git vault the git call fails and we return {}, so callers fall
    back to filesystem mtime — the graph builds fine either way.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(VAULT), "log", "--name-only", "--format=%x00%ct"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    ts = 0.0
    seen: dict[str, float] = {}
    for line in out.splitlines():
        if line.startswith("\x00"):
            try:
                ts = float(line[1:])
            except ValueError:
                pass
        elif line and line not in seen:
            seen[line] = ts
    return seen


def frontmatter_aliases(text: str) -> list[str]:
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    fm = text[3:end]
    aliases: list[str] = []
    in_alias_block = False
    for line in fm.splitlines():
        m = ALIASES_LINE.match(line.strip())
        if m:
            aliases += [a.strip().strip("'\"") for a in m.group(1).split(",") if a.strip()]
            in_alias_block = False
            continue
        if line.strip() == "aliases:":
            in_alias_block = True
            continue
        if in_alias_block:
            m2 = ALIAS_ITEM.match(line)
            if m2:
                aliases.append(m2.group(1).strip().strip("'\""))
            else:
                in_alias_block = False
    return aliases


def resolve_vault() -> Path:
    args = sys.argv[1:]
    if "--vault" in args:
        i = args.index("--vault")
        if i + 1 < len(args):
            return Path(args[i + 1]).expanduser().resolve()
    cfg = load_config()
    if not cfg:
        print(SETUP_HINT, file=sys.stderr)
        sys.exit(1)
    return vault_path(cfg)


def main() -> None:
    global VAULT
    VAULT = resolve_vault()
    if not VAULT.is_dir():
        print(f"vault path is not a directory: {VAULT}", file=sys.stderr)
        sys.exit(1)
    out_path = graph_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    files = [
        p for p in VAULT.rglob("*.md")
        if not any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(VAULT).parts)
        and note_id(p) not in SKIP_NOTES
    ]
    nodes = {}
    resolve: dict[str, str] = {}
    texts: dict[str, str] = {}
    edited = last_edit_epochs()
    now = time.time()

    for p in files:
        nid = note_id(p)
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        texts[nid] = text
        rel = p.relative_to(VAULT)
        parts = rel.parts
        ts = edited.get(str(rel)) or p.stat().st_mtime
        nodes[nid] = {
            "id": nid,
            "title": p.stem,
            # top-level folder; root notes group as "root" (the split view keys on this)
            "folder": parts[0] if len(parts) > 1 else "root",
            "age_days": max(0, int((now - ts) / 86400)),
            "words": len(text.split()),
        }
        resolve.setdefault(p.stem.lower(), nid)
        resolve.setdefault(nid.lower(), nid)
        for alias in frontmatter_aliases(text):
            resolve.setdefault(alias.lower(), nid)

    weights: dict[tuple[str, str], int] = {}
    for nid, text in texts.items():
        for m in WIKILINK.finditer(text):
            target = resolve.get(m.group(1).strip().lower())
            if target and target != nid:
                key = (nid, target)
                weights[key] = weights.get(key, 0) + 1

    degree: dict[str, int] = {}
    for (a, b) in weights:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    for nid, node in nodes.items():
        node["degree"] = degree.get(nid, 0)
        # planet mass: links + content, log-scaled so transcripts don't become suns
        node["mass"] = round(1 + 0.3 * node["degree"] + math.log2(1 + node["words"] / 100), 2)

    out = {
        "generated": time.time(),
        "vault": str(VAULT),
        "nodes": list(nodes.values()),
        "links": [{"source": a, "target": b, "weight": w} for (a, b), w in weights.items()],
    }
    out_path.write_text(json.dumps(out))
    print(
        f"graph: {len(nodes)} nodes, {len(out['links'])} links "
        f"({sum(weights.values())} raw wikilinks) in {time.time() - t0:.2f}s",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
