"""Video file controller — read video frames → detection pipeline.

Replaces camera SDK for demo mode. Shares stream_state + PipelineRunner
with CameraController so the frontend polling is identical.

Usage (via API):
    POST /detect/stream/start-video  { video_path: "video/xxx.mp4", fps: 10, loop: true }
    POST /detect/stream/stop-video
"""

import json
import logging
import os
import threading
import time

import cv2
import numpy as np

from backend.app.services.pipeline import PipelineRunner
from backend.app.services.stream_state import stream_state
from core_engine.config import get_risk_level

logger = logging.getLogger(__name__)


class VideoController:
    """Reads video file frames, runs detection pipeline, pushes to stream_state.

    Lifecycle: __init__ → start(video_path) → [worker loop] → stop()
    """

    _DB_BATCH_SIZE = 10

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._pipeline: PipelineRunner | None = None
        self._live_dir: str = ""
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._total_frames = 0
        self._start_time: float = 0.0
        self._video_path: str = ""
        self._fps: float = 10.0
        self._loop: bool = False

    def configure(self, pipeline: PipelineRunner, live_dir: str) -> None:
        self._pipeline = pipeline
        self._live_dir = live_dir
        os.makedirs(live_dir, exist_ok=True)

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self, video_path: str, fps: float = 10.0, loop: bool = False) -> dict:
        """Open video file, spawn worker thread.

        Returns: {"status": "started"} | {"status": "error", "detail": "..."}
        """
        if self._running:
            return {"status": "error", "detail": "Video stream already running. Stop first."}

        if self._pipeline is None:
            return {"status": "error", "detail": "VideoController not configured (no pipeline)."}

        if not os.path.isfile(video_path):
            return {"status": "error", "detail": f"Video file not found: {video_path}"}

        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            return {"status": "error", "detail": f"Failed to open video: {video_path}"}

        self._video_path = video_path
        self._fps = fps
        self._loop = loop
        self._running = True
        self._total_frames = 0
        self._start_time = time.time()

        # Clear old live images
        if self._live_dir and os.path.isdir(self._live_dir):
            for fname in os.listdir(self._live_dir):
                if fname.startswith("raw_") or fname.startswith("result_"):
                    try:
                        os.remove(os.path.join(self._live_dir, fname))
                    except OSError:
                        pass

        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

        logger.info(f"Video stream started: {video_path} @ {fps} fps (loop={loop})")
        return {"status": "started", "video_path": video_path, "fps": fps, "loop": loop}

    def stop(self) -> dict:
        """Stop worker thread, release video."""
        self._running = False

        if self._worker_thread is not None:
            self._worker_thread.join(timeout=5.0)
            self._worker_thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        logger.info("Video stream stopped.")
        return {"status": "stopped"}

    def is_active(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        return {
            "active": self._running,
            "source": "video",
            "video_path": self._video_path,
            "total_frames": self._total_frames,
            "elapsed_seconds": round(elapsed, 1),
            "effective_fps": round(self._total_frames / max(elapsed, 0.001), 2),
            "loop": self._loop,
            "target_fps": self._fps,
        }

    # ── Worker ───────────────────────────────────────────────────

    def _worker(self) -> None:
        _JPEG_QUALITY = 90
        _JPEG_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]
        _db_batch: list[tuple] = []
        interval = 1.0 / max(self._fps, 0.1)

        frame_id = 0
        last_read = 0.0

        while self._running:
            now = time.time()
            if now - last_read < interval:
                time.sleep(0.01)
                continue

            if self._cap is None:
                break

            ret, frame_bgr = self._cap.read()
            if not ret:
                if self._loop:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame_bgr = self._cap.read()
                    if not ret:
                        time.sleep(0.5)
                        continue
                else:
                    logger.info("Video ended. Stopping.")
                    self._running = False
                    break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            last_read = now
            frame_id += 1
            self._total_frames = frame_id

            try:
                # Pipeline
                result = self._pipeline.run_ndarray(frame_rgb)
                detections = result.get("detections", [])
                result_image = result.get("result_image")

                # Save raw
                raw_name = f"raw_{frame_id:06d}.jpg"
                raw_path = os.path.join(self._live_dir, raw_name)
                cv2.imwrite(raw_path, frame_bgr, _JPEG_PARAMS)

                # Save result
                result_name = f"result_{frame_id:06d}.jpg"
                result_path = os.path.join(self._live_dir, result_name)
                if result_image is not None:
                    cv2.imwrite(result_path,
                                cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR),
                                _JPEG_PARAMS)
                else:
                    cv2.imwrite(result_path, frame_bgr, _JPEG_PARAMS)

                # Risk level
                risk_levels = [get_risk_level(d["class_name"]) for d in detections]
                if "high" in risk_levels:
                    overall_risk = "high"
                elif "medium" in risk_levels:
                    overall_risk = "medium"
                else:
                    overall_risk = "low"

                det_list = []
                for d in detections:
                    det_list.append({
                        "class_id": d.get("class_id", -1),
                        "class_name": d.get("class_name", ""),
                        "class_name_zh": d.get("class_name_zh", ""),
                        "confidence": d.get("confidence", 0.0),
                        "bbox": d.get("bbox", []),
                        "risk_level": d.get("risk_level", "low"),
                    })

                stream_result = {
                    "id": f"vid_{frame_id:06d}",
                    "filename": f"vid_{frame_id:06d}",
                    "detections": det_list,
                    "frame_id": frame_id,
                    "risk_level": overall_risk,
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "q_score": result.get("q_score", 0.0),
                    "model": result.get("model", ""),
                }

                raw_url = f"/static/live/{raw_name}"
                result_url = f"/static/live/{result_name}"
                stream_state.add_result(stream_result, raw_image_url=raw_url,
                                        result_image_url=result_url)

                # Batch DB writes
                _db_batch.append((
                    f"vid_{frame_id:06d}", f"vid_{frame_id:06d}",
                    raw_url, result_url,
                    json.dumps(det_list),
                    result.get("q_score", 0.0),
                    overall_risk,
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                ))
                if len(_db_batch) >= self._DB_BATCH_SIZE:
                    self._flush_db_batch(_db_batch)
                    _db_batch.clear()

            except Exception:
                logger.exception(f"Worker error on video frame {frame_id}, skipping.")

        if _db_batch:
            self._flush_db_batch(_db_batch)

        logger.info(f"Video worker stopped. Total frames: {frame_id}")

    def _flush_db_batch(self, batch: list[tuple]) -> None:
        """Insert batch into history.db (lazy import to avoid circular deps)."""
        import sqlite3
        try:
            from backend.app.config import DATA_DIR
            db_path = os.path.join(DATA_DIR, "history.db")
            conn = sqlite3.connect(db_path)
            conn.executemany(
                "INSERT OR REPLACE INTO detection_history "
                "(id, filename, image_path, result_path, detections, q_score, risk_level, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            conn.commit()
            conn.close()
        except Exception:
            logger.exception("DB batch write failed")


# Module-level singleton
video_controller = VideoController()
