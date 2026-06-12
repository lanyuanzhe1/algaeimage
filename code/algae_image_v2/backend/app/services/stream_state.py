"""In-memory stream state — lightweight buffer for live-detection results.

No database, no disk I/O.  Stores the N most recent detection results
plus a simple status counter.  Thread-safe via a single lock.
"""
import threading
import time
from typing import Optional

# Maximum number of recent results to keep in memory
MAX_RESULTS = 200


class StreamState:
    """Singleton-style in-memory store for live detection stream."""

    def __init__(self):
        self._lock = threading.Lock()
        self._results: list[dict] = []       # newest first
        self._total_frames = 0
        self._start_time: Optional[float] = None

    # ── write side (called from POST /detect) ──────────────────

    def add_result(self, result: dict, raw_image_url: str = "", result_image_url: str = "") -> None:
        """Push a detection result into the buffer."""
        with self._lock:
            if self._start_time is None:
                self._start_time = time.time()
            self._total_frames += 1
            result["raw_image_url"] = raw_image_url
            result["result_image_url"] = result_image_url
            self._results.insert(0, result)
            # Trim to max size
            if len(self._results) > MAX_RESULTS:
                self._results = self._results[:MAX_RESULTS]

    # ── read side (called from GET polling endpoints) ──────────

    def get_latest(self, n: int = 10) -> list[dict]:
        """Return the N most recent results (newest first)."""
        with self._lock:
            return list(self._results[:n])

    def get_status(self) -> dict:
        """Return current stream status."""
        with self._lock:
            elapsed = time.time() - self._start_time if self._start_time else 0.0
            return {
                "active": self._start_time is not None,
                "total_frames": self._total_frames,
                "buffer_size": len(self._results),
                "elapsed_seconds": round(elapsed, 1),
                "effective_fps": round(self._total_frames / max(elapsed, 0.001), 2),
            }

    def reset(self) -> None:
        """Clear all state (for restart)."""
        with self._lock:
            self._results.clear()
            self._total_frames = 0
            self._start_time = None


# Module-level singleton
stream_state = StreamState()
