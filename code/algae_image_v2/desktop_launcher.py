"""Desktop launcher for Algae Image V2 — PyInstaller entry point.

Starts uvicorn, opens the browser, and handles graceful shutdown.
"""
import os
import sys
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

    print("=" * 50)
    print("  Algae Image V2")
    print("  FMPD Bright-field Algae Detection")
    print(f"  {url}")
    print("  Press Ctrl+C to exit")
    print("=" * 50)

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
