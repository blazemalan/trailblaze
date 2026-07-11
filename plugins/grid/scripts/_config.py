#!/usr/bin/env python3
"""Shared config + state-path resolution for The Grid.

Plugin installs are read-only and the plugin dir can be garbage-collected on
update, so ALL mutable state (config, graph.json, activity log, venv) lives
under a fixed home dir instead. Default is ~/.trailblaze/grid; the
TRAILBLAZE_GRID_HOME env var overrides it (tests + non-standard installs), and
every path below resolves under that one home.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SETUP_HINT = (
    'The Grid is not configured yet. Run the grid skill to set it up '
    '(say "set up the grid").'
)


def home() -> Path:
    override = os.environ.get("TRAILBLAZE_GRID_HOME")
    base = Path(override) if override else Path("~/.trailblaze/grid")
    return base.expanduser()


def config_path() -> Path:
    return home() / "config.json"


def graph_path() -> Path:
    return home() / "graph.json"


def log_path() -> Path:
    return home() / "activity.jsonl"


def venv_python() -> Path:
    return home() / "venv" / "bin" / "python"


def load_config() -> dict | None:
    """Parsed config, or None if it is missing / unreadable / has no vault."""
    try:
        cfg = json.loads(config_path().read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(cfg, dict) or not cfg.get("vault"):
        return None
    return cfg


def vault_path(cfg: dict) -> Path:
    return Path(cfg["vault"]).expanduser().resolve()


def config_port(cfg: dict) -> int:
    try:
        return int(cfg.get("port", 19333))
    except (TypeError, ValueError):
        return 19333
