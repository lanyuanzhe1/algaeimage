---
name: algae-v2-launcher
description: Start, stop, or restart the Algae Image V2 product. Use this skill when the user says "启动产品", "启动软件", "关闭产品", "关闭软件", "重启产品", "重启软件", "start the app", "stop the app", "restart the app", or mentions launching/shutting down the algae detection software.
---

# Algae Image V2 Launcher

Control the V2 product lifecycle — start, stop, or restart the FastAPI backend + browser frontend.

## Key facts

- **Project root**: `e:/code/codex/code/algae_image_v2`
- **Python**: `"A:/Anaconda_envs/envs/ican/python.exe"` (conda `ican`, must use full path — `conda activate` does not work in Git Bash)
- **Entry point**: uvicorn directly — `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` (NEVER use `desktop_launcher.py` — it auto-opens the default browser which may be Edge, not Firefox)
- **Browser**: Firefox ONLY — `"C:/Program Files/Mozilla Firefox/firefox.exe"`
- **Frontend URL**: `http://127.0.0.1:8000/app/`
- **API docs**: `http://127.0.0.1:8000/docs`
- **Port**: 8000

## Start

1. Check if port 8000 is already in use:
   ```bash
   "A:/Anaconda_envs/envs/ican/python.exe" -c "import socket; s=socket.socket(); r=s.connect_ex(('127.0.0.1',8000)); s.close(); print('BUSY' if r==0 else 'FREE')"
   ```
2. If BUSY, tell the user the port is occupied and ask if they want to kill processes first.
3. If FREE, launch uvicorn directly in background (NOT `desktop_launcher.py` — it would open Edge):
   ```bash
   cd e:/code/codex/code/algae_image_v2 && "A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
   Use `run_in_background: true` with a 10s timeout.
4. Wait 5 seconds, then check the output file for startup success. Look for `"Application startup complete"` and `"Uvicorn running on"`.
5. Once confirmed running, open Firefox and ONLY Firefox:
   ```bash
   "C:/Program Files/Mozilla Firefox/firefox.exe" "http://127.0.0.1:8000/app/" &
   ```
6. Report to the user: server state, URLs, and that Firefox has been opened.

## Stop

1. Find the background task running uvicorn and call `TaskStop` on it.
2. Kill remaining Python and Firefox processes:
   ```bash
   /c/Windows/System32/taskkill.exe //F //IM python.exe 2>&1
   /c/Windows/System32/taskkill.exe //F //IM firefox.exe 2>&1
   ```
3. Confirm to the user that all processes have been terminated.

## Restart

1. Run the **Stop** steps first.
2. Check port is free. If not, wait 3 seconds and check again — Windows TIME_WAIT can hold the port for up to 120s.
3. Run the **Start** steps.

## Troubleshooting

- **Port 8000 in use (errno 10048)**: A previous instance left the port in TIME_WAIT. Kill remaining Python processes, wait a few seconds, retry.
- **Python processes linger after task stop**: Use `taskkill.exe` with full Windows path to force-kill all Python processes.
- **Firefox opens but backend fails**: Check whether RDN/Stokes DLL weights exist in `weights/` directory.
- **Edge opened instead of Firefox**: You used `desktop_launcher.py` — don't. Always use uvicorn directly + explicit Firefox launch.
