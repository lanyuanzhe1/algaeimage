"""Desktop launcher for Algae Image V2 — PyInstaller entry point.

Starts uvicorn, opens the browser, and handles graceful shutdown.
"""
import os
import sys

# In PyInstaller console=False mode, stdout/stderr are None because
# the Windows GUI bootloader (runw.exe) does not attach a console.
# uvicorn's ColourizedFormatter calls sys.stdout.isatty() and crashes
# if stdout is None. Redirect to devnull so isatty() returns False.
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

import threading
import webbrowser


def _open_browser(url: str, delay: float = 2.0):
    """Open browser after a short delay to let uvicorn start."""
    import time
    time.sleep(delay)
    webbrowser.open(url)


def main():
    import uvicorn

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/app/"

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
