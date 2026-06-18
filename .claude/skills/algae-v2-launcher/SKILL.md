---
name: algae-v2-launcher
description: Start, stop, or restart the Algae Image V2 product. Use this skill when the user says "启动产品", "启动软件", "关闭产品", "关闭软件", "重启产品", "重启软件", "start the app", "stop the app", "restart the app", or mentions launching/shutting down the algae detection software.
---

# Algae Image V2 Launcher

Control the V2 product lifecycle.

## Primary method: Windows .bat scripts (recommended for demos)

Two scripts at repo root, double-clickable in Explorer. Zero dependency on Claude / Git Bash / terminal.

| Script | Location | What it does |
|--------|----------|--------------|
| `start.bat` | `e:/code/codex/start.bat` | Kill stale processes → start uvicorn in new window → wait for ready → open Firefox |
| `stop.bat` | `e:/code/codex/stop.bat` | Kill all Python + Firefox processes |

**How to use:** Simply tell the user to double-click `start.bat` / `stop.bat` in File Explorer.

**What start.bat does internally:**

1. `netstat` check port 8000 — if busy, auto-kill stale Python
2. `start "AlgaeV2-Server"` launches uvicorn in a titled cmd window (visible, easy to spot and close manually)
3. Polls `curl http://127.0.0.1:8000/docs` until HTTP 200 — never opens Firefox before backend is ready
4. Opens Firefox to `/app/`
5. Prints summary with all URLs

**What stop.bat does internally:**

1. `taskkill /F /IM python.exe` — all Python
2. `taskkill /F /IM firefox.exe` — all Firefox
3. Prints done

## Fallback: manual CLI (if .bat unavailable)

### Key facts

- **Project root**: `e:/code/codex/code/algae_image_v2`
- **Python**: `"A:/Anaconda_envs/envs/ican/python.exe"` (conda `ican`; `conda activate` does not work in Git Bash)
- **Entry point**: uvicorn directly — NEVER use `desktop_launcher.py` (it opens default browser = Edge)
- **Browser**: Firefox ONLY — `"C:/Program Files/Mozilla Firefox/firefox.exe"`
- **Port**: 8000

### Start (manual)

1. Check port:
   ```bash
   "A:/Anaconda_envs/envs/ican/python.exe" -c "import socket; s=socket.socket(); r=s.connect_ex(('127.0.0.1',8000)); s.close(); print('BUSY' if r==0 else 'FREE')"
   ```
2. If BUSY, kill processes first.
3. Launch in background:
   ```bash
   cd e:/code/codex/code/algae_image_v2 && "A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
4. Wait 5s, check output for `"Application startup complete"`.
5. Open Firefox:
   ```bash
   "C:/Program Files/Mozilla Firefox/firefox.exe" "http://127.0.0.1:8000/app/" &
   ```

### Stop (manual)

1. `TaskStop` the background task.
2. Kill processes:
   ```bash
   /c/Windows/System32/taskkill.exe //F //IM python.exe 2>&1
   /c/Windows/System32/taskkill.exe //F //IM firefox.exe 2>&1
   ```

### Restart (manual)

Stop → wait 3s for TIME_WAIT → Start.

## Troubleshooting

- **Port 8000 in use (errno 10048)**: TIME_WAIT from previous process. Kill Python processes, wait a few seconds, retry.
- **Edge opened instead of Firefox**: You used `desktop_launcher.py`. Use uvicorn directly + explicit Firefox.
- **Firefox opens but backend fails**: Check `weights/` directory for RDN/YOLO files.
