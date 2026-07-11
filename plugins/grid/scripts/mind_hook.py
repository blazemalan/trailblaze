#!/usr/bin/env python3
"""The Grid capture hook. Never blocks, never errors the session.

PostToolUse: emits read/edit/sweep events for vault files.
UserPromptSubmit (argv[1] == "prompt"): emits a prompt marker (starts the
slow-fade clock on prior flares; no prompt text is stored, by design).

Stdlib only, so the hook runs without the server's venv. When the grid is not
configured it drains stdin and returns without writing anything.
"""
from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from pathlib import Path

from _config import load_config, log_path, vault_path

VAULT: Path | None = None  # set in main() from config
LOG: Path | None = None     # set in main() from config
MAX_BYTES = 5_000_000  # rotate to .1 beyond this

READ_TOOLS = {"Read"}
EDIT_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
SWEEP_TOOLS = {"Grep", "Glob"}


def vault_rel(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        p = Path(raw).expanduser().resolve()
        rel = p.relative_to(VAULT)
    except (ValueError, OSError):
        return None
    if any(part.startswith(".") for part in rel.parts):
        return None
    return str(rel).removesuffix(".md")


def emit(event: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if LOG.exists() and LOG.stat().st_size > MAX_BYTES:
        LOG.replace(LOG.with_suffix(".jsonl.1"))
    with open(LOG, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(event) + "\n")


def main() -> None:
    global VAULT, LOG
    cfg = load_config()
    raw = sys.stdin.read()  # always drain the pipe, even when unconfigured
    if not cfg:
        return  # grid not set up yet: silent no-op
    VAULT = vault_path(cfg)
    LOG = log_path()

    base = {"ts": time.time(), "agent": "claude"}
    if len(sys.argv) > 1 and sys.argv[1] == "prompt":
        # Flares hold until the user's next prompt. Task notifications, command
        # output, and other system turns must not start the fade clock.
        try:
            text = json.loads(raw).get("prompt", "")
        except (json.JSONDecodeError, AttributeError):
            text = raw
        if not text.strip():
            return
        if any(m in text for m in ("<task-notification>", "<local-command", "<command-name>", "SYSTEM NOTIFICATION")):
            return
        emit({**base, "action": "prompt"})
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input", {}) or {}

    if tool in READ_TOOLS or tool in EDIT_TOOLS:
        note = vault_rel(ti.get("file_path") or ti.get("notebook_path"))
        if note:
            action = "read" if tool in READ_TOOLS else "edit"
            emit({**base, "action": action, "note": note})
    elif tool in SWEEP_TOOLS:
        target = ti.get("path") or os.getcwd()
        try:
            rel = Path(target).expanduser().resolve().relative_to(VAULT)
            folder = rel.parts[0] if rel.parts else ""
        except (ValueError, OSError):
            return
        emit({**base, "action": "sweep", "folder": folder})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a broken viz hook must never break the session
    sys.exit(0)
