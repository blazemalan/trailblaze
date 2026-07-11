#!/usr/bin/env python3
"""The Grid doctor: preflight + health check. Stdlib only.

Runs six checks, each printing PASS / FAIL / INFO with a fix hint. Exits 1 if
any hard check fails, so it doubles as a setup gate for the grid skill.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from _config import (
    config_path,
    config_port,
    graph_path,
    load_config,
    log_path,
    venv_python,
    vault_path,
)

HERE = Path(__file__).resolve().parent

OK = "✅"    # PASS
BAD = "❌"   # FAIL
INFO = "ℹ️"  # info only

_failed = False


def line(mark: str, msg: str, hint: str | None = None) -> None:
    print(f"{mark} {msg}")
    if hint:
        print(f"   → {hint}")


def fail(msg: str, hint: str | None = None) -> None:
    global _failed
    _failed = True
    line(BAD, msg, hint)


def check_config():
    """1. config.json exists + vault is a real dir with .md files."""
    cfg = load_config()
    if not cfg:
        fail(
            f"config not found or invalid ({config_path()})",
            'run the grid skill to set it up (say "set up the grid")',
        )
        return None
    vault = vault_path(cfg)
    if not vault.is_dir():
        fail(f"vault path is not a directory: {vault}",
             "fix the vault path in config.json")
        return cfg
    has_md = any(True for _ in vault.rglob("*.md"))
    if not has_md:
        fail(f"no .md files under {vault}", "point the vault at a Markdown vault")
        return cfg
    line(OK, f"config ok; vault {vault} has Markdown files")
    return cfg


def check_deps():
    """2. fastapi + uvicorn importable from the state venv."""
    py = venv_python()
    if not py.exists():
        fail(f"venv not found ({py})",
             'python3 -m venv "$HOME/.trailblaze/grid/venv" && '
             '"$HOME/.trailblaze/grid/venv/bin/pip" install fastapi uvicorn')
        return
    try:
        r = subprocess.run([str(py), "-c", "import fastapi, uvicorn"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        fail(f"could not run the venv python: {e}")
        return
    if r.returncode != 0:
        fail("fastapi/uvicorn not importable from the venv",
             f'"{py.parent}/pip" install fastapi uvicorn')
        return
    line(OK, "server deps present (fastapi, uvicorn)")


def check_graph():
    """3. graph builds; report node/link counts (warn, don't fail, on 0)."""
    try:
        r = subprocess.run([sys.executable, str(HERE / "build_graph.py")],
                           capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        fail(f"build_graph did not run: {e}")
        return
    if r.returncode != 0:
        fail("build_graph failed", (r.stderr or "").strip() or "see output above")
        return
    try:
        g = json.loads(graph_path().read_text())
        nodes, links = len(g.get("nodes", [])), len(g.get("links", []))
    except (OSError, ValueError):
        fail(f"graph.json unreadable ({graph_path()})")
        return
    if nodes == 0:
        line(INFO, "graph built but has 0 nodes (empty vault, or all notes skipped)")
    else:
        line(OK, f"graph builds: {nodes} nodes, {links} links")


def check_git(cfg):
    """4. is the vault a git repo? Info only (PULSE degrades to mtimes)."""
    if not cfg:
        return
    vault = vault_path(cfg)
    is_git = (vault / ".git").exists()
    if is_git:
        line(INFO, "vault is a git repo (PULSE uses commit history for recency)")
    else:
        line(INFO, "vault is not a git repo (PULSE falls back to file mtimes)")


def check_server(cfg):
    """5. server answers /graph.json on the configured port."""
    port = config_port(cfg) if cfg else 19333
    url = f"http://127.0.0.1:{port}/graph.json"
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            code = resp.status
    except (urllib.error.URLError, OSError):
        code = None
    if code == 200:
        line(OK, f"server responds on 127.0.0.1:{port}")
    else:
        fail(
            f"server not responding on 127.0.0.1:{port}",
            f'start it: nohup "$HOME/.trailblaze/grid/venv/bin/python" '
            f'"{HERE / "server.py"}" >/tmp/trailblaze-grid.log 2>&1 &',
        )


def check_activity():
    """6. activity log exists + hook wrote recently (info only)."""
    log = log_path()
    if not log.exists():
        line(INFO, "no agent activity logged yet (fine on day one)")
        return
    try:
        mtime = log.stat().st_mtime
    except OSError:
        line(INFO, "activity log present")
        return
    age_h = (time.time() - mtime) / 3600
    if age_h <= 24:
        line(OK, f"activity logged in the last 24h ({age_h:.1f}h ago)")
    else:
        line(INFO, f"no activity in {age_h:.0f}h (hook only fires in Claude Code sessions)")


def main() -> None:
    cfg = check_config()
    check_deps()
    check_graph()
    check_git(cfg)
    check_server(cfg)
    check_activity()
    print()
    if _failed:
        print("Some checks failed. Fix the items marked above, then re-run the doctor.")
        sys.exit(1)
    print("The Grid looks healthy.")


if __name__ == "__main__":
    main()
