---
name: grid
description: >
  Set up, launch, or troubleshoot The Grid: a live 3D mind-graph of a
  Markdown vault that lights up in real time as the agent reads and edits
  notes. Triggers on "set up the grid", "launch the grid", "fix the grid",
  "mind graph", "brain graph", "visualize my second brain", or "watch the
  agent think". Conversational installer + day-to-day operator.
---

# The Grid: a live window into an agent working your vault

The Grid renders a vault as a galaxy: every note is a planet (sized by links +
words), every `[[wikilink]]` is an orbit. As a Claude Code agent reads and edits
notes, those planets flare orange and the walked route lights as a path — so you
*watch* the agent think instead of reading a log. It is read-only and local: the
only text that ever renders is note filenames.

**Two moving parts.** A hook (auto-registered by this plugin) appends one line to
an activity log every time the agent touches a vault file. A small local server
serves the viewer and streams that log to the browser. All state lives outside
the plugin, under `~/.trailblaze/grid/` (override with the `TRAILBLAZE_GRID_HOME`
env var), because plugin dirs are read-only and get garbage-collected on update.

**Requirements.** macOS or Linux (the hook uses `fcntl`), `python3` ≥ 3.10 with
`pip`/`venv`, an Obsidian-style Markdown vault, and Claude Code as the daily
driver. A box that stays on is what makes it "live".

Script paths below use `${CLAUDE_PLUGIN_ROOT}` (the installed plugin dir). When
you run these steps, substitute the real path. `<HOME>` below means
`~/.trailblaze/grid` unless `TRAILBLAZE_GRID_HOME` is set.

## Install (first run)

Walk the user through these steps, running each one and reporting results.

### 1. Prereqs + pick the vault

- Check `python3 --version` is ≥ 3.10 and `python3 -m pip --version` works. If
  not, stop and tell the user what to install.
- Pick the vault. **Default to the current directory** if it looks like a vault
  (contains an `.obsidian/` folder, or wiki-style top-level folders with `.md`
  files). Otherwise ask the user for the path and suggest `~/second-brain`.
  Confirm the choice before writing config.

### 2. Create state dir, config, and the venv

```bash
mkdir -p "$HOME/.trailblaze/grid"
# config.json — vault is required, port defaults to 19333
printf '{"vault": "%s", "port": 19333}\n' "/abs/path/to/vault" > "$HOME/.trailblaze/grid/config.json"
python3 -m venv "$HOME/.trailblaze/grid/venv"
"$HOME/.trailblaze/grid/venv/bin/pip" install --quiet --upgrade pip fastapi uvicorn
```

(If `TRAILBLAZE_GRID_HOME` is set, use it in place of `$HOME/.trailblaze/grid`
everywhere.)

### 3. Build the graph

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py"
```

Report the node/link counts it prints. Zero nodes means the vault path is wrong
or the vault has no `.md` files — recheck step 1.

### 4. Start the server, then run the doctor

```bash
nohup "$HOME/.trailblaze/grid/venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/server.py" \
  > /tmp/trailblaze-grid.log 2>&1 &
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

The doctor prints a checklist (config, deps, graph, git, server, activity) and
exits non-zero if anything hard is wrong. Fix anything marked ❌ and re-run it.

### 5. Open it, then just work

Tell the user: open **http://127.0.0.1:19333** in a browser, then go back to
working in Claude Code. Notes light up as the agent reads and edits them; the
chips at the bottom (SPLIT FOLDERS / PULSE · REPLAY · TUNE) split the galaxy by
folder or recency, replay past attention runs, and tune the layout live.

**Remote / phone viewing is out of scope for this installer.** The server binds
`127.0.0.1` on purpose. If you want to view it from another device, put that
device on the same machine's private network (a tailnet or VPN you run yourself)
and reach `127.0.0.1` through that tunnel. **Never expose the port to the public
internet** — note *titles* render in the viewer, so an open port leaks your
filenames to anyone who finds it.

## Keep it running (optional)

The `nohup` above dies when the machine reboots. To keep The Grid always-on,
install one of these. Both are optional; fill in the real venv path and
`${CLAUDE_PLUGIN_ROOT}`.

**macOS — launchd** (`~/Library/LaunchAgents/com.trailblaze.grid.plist`, then
`launchctl load` it):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.trailblaze.grid</string>
  <key>ProgramArguments</key>
  <array>
    <string>/ABS/PATH/.trailblaze/grid/venv/bin/python</string>
    <string>/ABS/PATH/TO/PLUGIN/scripts/server.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardErrorPath</key><string>/tmp/trailblaze-grid.log</string>
</dict></plist>
```

**Linux — systemd user unit**
(`~/.config/systemd/user/trailblaze-grid.service`, then
`systemctl --user enable --now trailblaze-grid`):

```ini
[Unit]
Description=The Grid (Trailblaze)
[Service]
ExecStart=/ABS/PATH/.trailblaze/grid/venv/bin/python /ABS/PATH/TO/PLUGIN/scripts/server.py
Restart=on-failure
[Install]
WantedBy=default.target
```

## Operate (day to day)

| Task | Command |
|---|---|
| Rebuild the graph now | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py"` (the server also auto-rebuilds when vault files change) |
| Health check | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"` |
| Restart the server | kill the old process (`pkill -f scripts/server.py`), then re-run the `nohup … server.py &` line from step 4 |
| Point at a different vault | edit `vault` in `<HOME>/config.json`, then rebuild + restart |

After editing this plugin's hook files, run `/reload-plugins` so Claude Code
picks up the change.

### "Why is nothing lighting up?"

Triage in order:

1. **The hook only fires inside Claude Code sessions.** Editing the vault in
   Obsidian or another editor does not light the graph — the agent has to be the
   one reading/editing. Do some work in a Claude Code session pointed at the
   vault and watch.
2. **Config points at the right vault?** `cat <HOME>/config.json`. The hook
   silently no-ops (never errors your session) when the grid isn't configured or
   the file being touched is outside the vault.
3. **Server up?** The status dot (bottom-right) is orange when live, dim when
   stale. Re-run the doctor; if the server is down it prints the start command.
4. **Replay shows nothing?** Replay needs walked history — a fresh install has
   none until the agent has actually walked the vault for a while.
