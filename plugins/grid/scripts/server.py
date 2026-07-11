#!/usr/bin/env python3
"""The Grid server. Binds 127.0.0.1 only (host is not configurable).

Serves the viewer, graph.json (rebuilt with a debounce when the vault
changes), and /events: SSE that replays a recent-history buffer on connect
(so opening mid-thought never shows a blank grid) then live-tails the
activity log. Vault path, log, graph, and port come from the grid config.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

from _config import SETUP_HINT, config_port, graph_path, load_config, log_path, vault_path

HERE = Path(__file__).resolve().parent
VIEWER = HERE.parent / "viewer"

# Resolve config before importing the server deps, so a missing config prints a
# clear hint instead of an ImportError if the venv isn't active.
_cfg = load_config()
if _cfg is None:
    print(SETUP_HINT, file=sys.stderr)
    sys.exit(1)

VAULT = vault_path(_cfg)
LOG = log_path()
GRAPH = graph_path()
PORT = config_port(_cfg)
HISTORY_SECONDS = 30 * 60
REBUILD_DEBOUNCE = 5.0

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

app = FastAPI()
_last_rebuild_check = 0.0


def vault_mtime() -> float:
    newest = 0.0
    for p in VAULT.rglob("*.md"):
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            continue
    return newest


def ensure_graph() -> None:
    global _last_rebuild_check
    now = time.time()
    if now - _last_rebuild_check < REBUILD_DEBOUNCE:
        return
    _last_rebuild_check = now
    if not GRAPH.exists() or vault_mtime() > GRAPH.stat().st_mtime:
        subprocess.run([sys.executable, str(HERE / "build_graph.py")], timeout=60)


NO_STORE = {"Cache-Control": "no-store"}


# The galaxy is the only view; /3d is an alias for / so older bookmarks and
# links keep working.
@app.get("/")
@app.get("/3d")
def index():
    return FileResponse(VIEWER / "3d.html", headers=NO_STORE)


@app.get("/3d-force-graph.min.js")
def three_lib():
    return FileResponse(VIEWER / "3d-force-graph.min.js", media_type="text/javascript")


@app.get("/graph.json")
def graph():
    ensure_graph()
    return FileResponse(GRAPH, media_type="application/json", headers=NO_STORE)


@app.get("/walks.json")
def walks():
    """The persisted stream grouped into walks: prompt-to-prompt attention runs.

    Replay's menu. Newest first, capped at the most recent 200 walks (older
    ones are still in the log, just not listed). Consecutive repeats of the
    same note+action collapse to one event so a re-read loop doesn't pad the
    count.
    """
    walks_list: list[dict] = []
    cur: dict | None = None

    def close(w):
        if w and w["events"]:
            w["end"] = w["events"][-1]["ts"]
            w["count"] = len(w["events"])
            walks_list.append(w)

    if LOG.exists():
        with open(LOG) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                action = ev.get("action")
                if action == "prompt":
                    close(cur)
                    cur = {"start": ev["ts"], "events": []}
                elif action in ("read", "edit") and ev.get("note"):
                    if cur is None:
                        cur = {"start": ev["ts"], "events": []}
                    prev = cur["events"][-1] if cur["events"] else None
                    if prev and prev["note"] == ev["note"] and prev["action"] == action:
                        continue
                    cur["events"].append(
                        {"ts": ev["ts"], "action": action, "note": ev["note"]})
    close(cur)
    return JSONResponse(list(reversed(walks_list[-200:])), headers=NO_STORE)


def history_lines() -> list[str]:
    if not LOG.exists():
        return []
    cutoff = time.time() - HISTORY_SECONDS
    out = []
    with open(LOG) as f:
        for line in f:
            try:
                if json.loads(line).get("ts", 0) >= cutoff:
                    out.append(line.rstrip("\n"))
            except json.JSONDecodeError:
                continue
    return out[-500:]


async def event_stream():
    for line in history_lines():
        yield f"data: {line}\n\n"
    yield f"data: {json.dumps({'action': 'live', 'ts': time.time()})}\n\n"
    offset = LOG.stat().st_size if LOG.exists() else 0
    last_beat = time.time()
    while True:
        await asyncio.sleep(0.5)
        if LOG.exists():
            size = LOG.stat().st_size
            if size < offset:  # rotated
                offset = 0
            if size > offset:
                with open(LOG) as f:
                    f.seek(offset)
                    chunk = f.read()
                    offset = f.tell()
                for line in chunk.splitlines():
                    if line.strip():
                        yield f"data: {line}\n\n"
        if time.time() - last_beat > 15:
            yield ": beat\n\n"
            last_beat = time.time()


@app.get("/events")
def events():
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    # SSE streams are infinite generators; without this cap a graceful shutdown
    # waits on them forever (alive process, closed listener).
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning",
                timeout_graceful_shutdown=3)
