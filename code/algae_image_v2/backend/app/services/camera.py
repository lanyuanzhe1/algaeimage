"""Camera controller — MVS SDK integration with worker thread.

Encapsulates SDK init, frame callbacks, and a background worker that
processes frames through the detection pipeline and pushes results to
the in-memory stream_state buffer.

Architecture:
    SDK callback → frame queue (thread-safe) → worker thread
        → save temp PNG → pipeline.run() → save raw/result PNGs
        → stream_state.add_result() → prune old images
"""
import ctypes
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from ctypes import POINTER, byref, cast, c_bool, c_void_p, memset

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# MVS SDK setup (module-level)
# ═══════════════════════════════════════════════════════════════
_MVS_DIR = r"A:\Program Files\MVS"
_MVIMP_DIR = os.path.join(_MVS_DIR, "Development", "Samples", "Python", "MvImport")
_DLL_DIR = r"C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64"

_sdk_available = False

if _MVIMP_DIR not in sys.path:
    sys.path.insert(0, _MVIMP_DIR)

# Must add DLL directory to PATH and loader BEFORE importing SDK classes
os.environ["PATH"] = _DLL_DIR + ";" + os.environ.get("PATH", "")
try:
    os.add_dll_directory(_DLL_DIR)
except AttributeError:
    pass  # Python < 3.8

try:
    from MvCameraControl_class import (  # noqa: E402
        MvCamera, MV_CC_DEVICE_INFO_LIST, MV_CC_DEVICE_INFO,
        MV_FRAME_OUT, MV_CC_HB_DECODE_PARAM, MV_CC_PIXEL_CONVERT_PARAM_EX,
        MV_ACCESS_Exclusive, MV_TRIGGER_MODE_OFF,
        MV_GIGE_DEVICE, MV_USB_DEVICE, MV_GENTL_GIGE_DEVICE,
        get_platform_functype,
        PixelType_Gvsp_Mono8, PixelType_Gvsp_RGB8_Packed,
        PixelType_Gvsp_Undefined,
    )
    _sdk_available = True
except ImportError:
    logger.warning("MVS SDK not available (non-Windows or MVS not installed). "
                   "CameraController will report 'camera not found' on start().")

# Pixel type constants for HB decode check
_PIXEL_TYPES_HB = {
    0x02180001, 0x02180003, 0x02180005, 0x02180007,  # Mono HB
    0x02180009, 0x0218000B, 0x0218000D, 0x0218000F, 0x02180011,
    0x02180013, 0x02180015,  # Bayer HB
    0x02280001, 0x02280003, 0x02280005, 0x02280007,  # RGB/BGR HB packed
    0x02280009, 0x0228000B, 0x0228000D, 0x0228000F,
    0x02280011, 0x02280013,  # YUV HB
}

MAX_LIVE_IMAGES = 50


class CameraController:
    """Encapsulates MVS SDK camera lifecycle and background processing.

    Lifecycle: __init__ → configure() → start() → [worker loop] → stop() → finalize()

    The worker thread dequeues the latest frame from the SDK callback queue,
    runs the detection pipeline, saves raw/result images to live_dir, and
    pushes results to stream_state for frontend polling.
    """

    def __init__(self):
        self._dev_info = None
        self._cam = None
        self._pipeline = None
        self._live_dir = ""
        self._running = False
        self._worker_thread = None
        self._total_frames = 0
        self._start_time: float = 0.0
        self._exposure_us: float = 5000.0  # default 5ms, 可调

        # Frame queue (callback → worker)
        self._frame_queue: list[np.ndarray] = []
        self._frame_lock = threading.Lock()

        if not _sdk_available:
            logger.warning("CameraController: SDK not available, camera operations will be no-ops.")
            return

        # ── Initialize SDK ───────────────────────────────────────
        ret = MvCamera.MV_CC_Initialize()
        if ret != 0:
            logger.warning(f"MV_CC_Initialize failed: 0x{ret:x}")
            return

        sdk_ver = MvCamera.MV_CC_GetSDKVersion()
        logger.info(f"MVS SDK version: 0x{sdk_ver:x}")

        # ── Enumerate devices ────────────────────────────────────
        deviceList = MV_CC_DEVICE_INFO_LIST()
        tlayer = MV_GIGE_DEVICE | MV_USB_DEVICE
        ret = MvCamera.MV_CC_EnumDevices(tlayer, deviceList)
        if ret == 0 and deviceList.nDeviceNum > 0:
            logger.info(f"Found {deviceList.nDeviceNum} device(s)")
            self._dev_info = cast(
                deviceList.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)
            ).contents
            if self._dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
                try:
                    name = (bytes(self._dev_info.SpecialInfo.stGigEInfo.chModelName)
                            .decode("ascii", errors="replace").strip("\x00"))
                    logger.info(f"GigE device: {name}")
                except Exception:
                    pass
        else:
            logger.warning("No camera found. Check GigE connection and MVS client.")

    # ── Configuration ────────────────────────────────────────────

    def configure(self, pipeline, live_dir: str) -> None:
        """Set the pipeline runner and output directory for live images.

        Args:
            pipeline: PipelineRunner instance (with pre-loaded YOLO model).
            live_dir: Directory path where raw/result PNGs will be saved.
        """
        self._pipeline = pipeline
        self._live_dir = live_dir
        os.makedirs(live_dir, exist_ok=True)

    # ── Frame decode ─────────────────────────────────────────────

    def _decode_frame(self, stFrame):
        """HB decode + pixel convert → RGB ndarray, or None on failure."""
        if not _sdk_available or self._cam is None:
            return None

        w = stFrame.stFrameInfo.nWidth
        h = stFrame.stFrameInfo.nHeight
        pixel_type = stFrame.stFrameInfo.enPixelType

        stDecodeParam = MV_CC_HB_DECODE_PARAM()
        stConvertParam = MV_CC_PIXEL_CONVERT_PARAM_EX()
        memset(byref(stConvertParam), 0, ctypes.sizeof(stConvertParam))

        if pixel_type in _PIXEL_TYPES_HB:
            decode_len = w * h * 3
            decode_buf = (ctypes.c_ubyte * decode_len)()
            stDecodeParam.pSrcBuf = stFrame.pBufAddr
            stDecodeParam.nSrcLen = stFrame.stFrameInfo.nFrameLen
            stDecodeParam.pDstBuf = decode_buf
            stDecodeParam.nDstBufSize = decode_len
            ret = self._cam.MV_CC_HBDecode(stDecodeParam)
            if ret != 0:
                return None
            stConvertParam.pSrcData = stDecodeParam.pDstBuf
            stConvertParam.nSrcDataLen = stDecodeParam.nDstBufLen
            stConvertParam.enSrcPixelType = stDecodeParam.enDstPixelType
        else:
            stConvertParam.pSrcData = stFrame.pBufAddr
            stConvertParam.nSrcDataLen = stFrame.stFrameInfo.nFrameLen
            stConvertParam.enSrcPixelType = pixel_type

        dst_ch = 3
        dst_len = dst_ch * w * h
        dst_buf = (ctypes.c_ubyte * dst_len)()
        stConvertParam.nWidth = w
        stConvertParam.nHeight = h
        stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
        stConvertParam.pDstBuffer = dst_buf
        stConvertParam.nDstBufferSize = dst_len

        ret = self._cam.MV_CC_ConvertPixelTypeEx(stConvertParam)
        if ret != 0:
            return None

        return np.frombuffer(dst_buf, dtype=np.uint8, count=dst_len).reshape(h, w, 3)

    # ── Callback factory ─────────────────────────────────────────

    def _make_callback(self):
        """Create SDK-compatible frame callback that pushes decoded frames to queue.

        The callback signature must match:
            void callback(MV_FRAME_OUT*, void* pUser, bool bAutoFree)
        """
        _functype = get_platform_functype()
        _FrameCallbackType = _functype(None, POINTER(MV_FRAME_OUT), c_void_p, c_bool)

        cam_ref = self._cam

        def _image_callback(pstFrame, pUser, bAutoFree):
            stFrame = cast(pstFrame, POINTER(MV_FRAME_OUT)).contents
            if not stFrame:
                return
            rgb = self._decode_frame(stFrame)
            if rgb is not None:
                with self._frame_lock:
                    self._frame_queue.append(rgb)
            if not bAutoFree and pUser is not None:
                cam_ref.MV_CC_FreeImageBuffer(stFrame)

        self._callback = _FrameCallbackType(_image_callback)

    # ── Worker thread ────────────────────────────────────────────

    def _worker(self):
        """Main processing loop: dequeue latest frame → pipeline → save → stream_state."""
        from backend.app.services.stream_state import stream_state
        from core_engine.config import get_risk_level

        # Batch DB writes: accumulate det_list strings, flush every BATCH_SIZE frames
        _db_batch: list[tuple] = []
        _DB_BATCH_SIZE = 10
        _JPEG_QUALITY = 90
        _JPEG_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]

        while self._running:
            # ── Pop latest frame (clear queue, take [-1]) ─────────
            with self._frame_lock:
                if self._frame_queue:
                    frame = self._frame_queue[-1]
                    self._frame_queue.clear()
                else:
                    frame = None

            if frame is None:
                time.sleep(0.02)
                continue

            frame_id = self._total_frames + 1
            self._total_frames = frame_id

            try:
                # Run pipeline directly on ndarray (no temp file I/O)
                result = self._pipeline.run_ndarray(frame)
                detections = result.get("detections", [])
                result_image = result.get("result_image")  # RGB ndarray

                # Save raw frame as JPEG (5-10x faster than PNG, smaller files)
                raw_name = f"raw_{frame_id:06d}.jpg"
                raw_path = os.path.join(self._live_dir, raw_name)
                cv2.imwrite(raw_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), _JPEG_PARAMS)

                # Save result image as JPEG
                result_name = f"result_{frame_id:06d}.jpg"
                result_path = os.path.join(self._live_dir, result_name)
                if result_image is not None:
                    cv2.imwrite(result_path, cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR), _JPEG_PARAMS)
                else:
                    result_image = self._draw_detection_boxes(frame.copy(), detections)
                    cv2.imwrite(result_path, cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR), _JPEG_PARAMS)

                # Compute overall risk level
                risk_levels = [get_risk_level(d["class_name"]) for d in detections]
                if "high" in risk_levels:
                    overall_risk = "high"
                elif "medium" in risk_levels:
                    overall_risk = "medium"
                else:
                    overall_risk = "low"

                # Build detection dicts
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
                    "id": f"live_{frame_id:06d}",
                    "filename": f"live_{frame_id:06d}",
                    "detections": det_list,
                    "frame_id": frame_id,
                    "risk_level": overall_risk,
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "q_score": result.get("q_score", 0.0),
                    "model": result.get("model", ""),
                }

                # Build relative URLs for frontend
                raw_url = f"/static/live/{raw_name}"
                result_url = f"/static/live/{result_name}"

                stream_state.add_result(stream_result, raw_image_url=raw_url,
                                        result_image_url=result_url)

                # Batch DB writes (flush every _DB_BATCH_SIZE frames)
                _db_batch.append((f"live_{frame_id:06d}", f"live_{frame_id:06d}",
                                  raw_url, result_url,
                                  json.dumps(det_list),
                                  result.get("q_score", 0.0),
                                  overall_risk,
                                  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
                if len(_db_batch) >= _DB_BATCH_SIZE:
                    self._flush_db_batch(_db_batch)
                    _db_batch.clear()

                # Prune old images
                self._prune_images()

            except Exception:
                logger.exception(f"Worker error on frame {frame_id}, skipping.")

        # Flush remaining DB records before exit
        if _db_batch:
            self._flush_db_batch(_db_batch)
            _db_batch.clear()

        logger.info("Worker thread stopped.")

    def _flush_db_batch(self, batch: list[tuple]) -> None:
        """Write a batch of detection records to SQLite in one transaction."""
        try:
            from backend.app.config import DB_PATH
            db_conn = sqlite3.connect(DB_PATH, timeout=5)
            db_conn.executemany(
                """INSERT OR REPLACE INTO detection_history
                       (id, filename, image_path, result_path, detections, q_score, risk_level, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                batch,
            )
            db_conn.commit()
            db_conn.close()
        except Exception:
            logger.exception("Failed to flush batch to history DB")

    # ── Image pruning ────────────────────────────────────────────

    def _prune_images(self):
        """Keep only the last MAX_LIVE_IMAGES frames (2 files each) in live_dir."""
        try:
            if not self._live_dir or not os.path.isdir(self._live_dir):
                return

            # Collect (frame_id, path) for all live images
            raw_files = []
            result_files = []
            for fname in os.listdir(self._live_dir):
                full = os.path.join(self._live_dir, fname)
                if not os.path.isfile(full):
                    continue
                try:
                    frame_id = int(fname.split("_")[1].split(".")[0])
                except (IndexError, ValueError):
                    continue
                if fname.startswith("raw_"):
                    raw_files.append((frame_id, full))
                elif fname.startswith("result_"):
                    result_files.append((frame_id, full))

            # Keep only MAX_LIVE_IMAGES most recent
            for file_list in [raw_files, result_files]:
                if len(file_list) > MAX_LIVE_IMAGES:
                    file_list.sort(key=lambda x: x[0], reverse=True)
                    for _, path in file_list[MAX_LIVE_IMAGES:]:
                        try:
                            os.remove(path)
                        except OSError:
                            pass
        except Exception:
            logger.exception("Error pruning live images.")

    # ── Detection box drawing (fallback) ─────────────────────────

    def _draw_detection_boxes(self, rgb: np.ndarray, detections: list) -> np.ndarray:
        """Draw detection boxes on RGB image. Returns RGB ndarray."""
        from core_engine.config import get_risk_color

        img = rgb.copy()
        for d in detections:
            bbox = d.get("bbox", [])
            if len(bbox) != 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bbox]
            color_hex = get_risk_color(d.get("risk_level", "low"))
            r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
            color_bgr = (b, g, r)
            cv2.rectangle(img, (x1, y1), (x2, y2), color_bgr, 6)
            label = f"{d.get('class_name','')} {d.get('confidence',0):.2f}"
            cv2.putText(img, label, (x1, max(y1 - 8, 30)),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, color_bgr, 4)
        return img

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self, exposure_us: float = 5000.0) -> dict:
        """Open device, register callback, start grabbing, spawn worker thread.

        exposure_us: exposure time in microseconds (default 5ms).
        Returns:
            {"status": "started"} on success,
            {"status": "error", "detail": "..."} on failure.
        """
        self._exposure_us = exposure_us
        if not _sdk_available:
            return {"status": "error", "detail": "MVS SDK not available"}

        if self._dev_info is None:
            return {"status": "error", "detail": "No camera found"}

        if self._pipeline is None:
            return {"status": "error", "detail": "Pipeline not configured"}

        if self._running:
            return {"status": "error", "detail": "Already running"}

        # ── Create handle + open ─────────────────────────────────
        self._cam = MvCamera()

        ret = self._cam.MV_CC_CreateHandle(self._dev_info)
        if ret != 0:
            logger.error(f"CreateHandle failed: 0x{ret:x}")
            self._cam = None
            return {"status": "error", "detail": f"CreateHandle failed: 0x{ret:x}"}

        ret = self._cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            err_detail = f"OpenDevice failed: 0x{ret:x}"
            if ret == 0x80000203:
                err_detail = "MVS device occupied (0x80000203). Close MVS client first."
            logger.error(err_detail)
            self._cam.MV_CC_DestroyHandle()
            self._cam = None
            return {"status": "error", "detail": err_detail}

        # GigE optimisation
        if self._dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
            pkt = self._cam.MV_CC_GetOptimalPacketSize()
            if pkt > 0:
                self._cam.MV_CC_SetIntValue("GevSCPSPacketSize", pkt)

        self._cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)

        # Exposure: disable auto, set manual (unit: microseconds)
        self._cam.MV_CC_SetEnumValue("ExposureAuto", 0)  # 0=Off
        time.sleep(0.2)  # 等待相机固件完成模式切换，否则 ExposureTime 节点锁住不可写
        ret = self._cam.MV_CC_SetFloatValue("ExposureTime", self._exposure_us)
        if ret != 0:
            logger.error(f"SetFloatValue ExposureTime failed: 0x{ret:x}")

        # Register callback
        self._make_callback()
        ret = self._cam.MV_CC_RegisterImageCallBackEx2(
            self._callback, ctypes.py_object(self._cam), True
        )
        if ret != 0:
            logger.error(f"RegisterImageCallBackEx2 failed: 0x{ret:x}")
            self._cam.MV_CC_CloseDevice()
            self._cam.MV_CC_DestroyHandle()
            self._cam = None
            return {"status": "error",
                    "detail": f"RegisterImageCallBackEx2 failed: 0x{ret:x}"}

        # Start grabbing
        ret = self._cam.MV_CC_StartGrabbing()
        if ret != 0:
            logger.error(f"StartGrabbing failed: 0x{ret:x}")
            self._cam.MV_CC_CloseDevice()
            self._cam.MV_CC_DestroyHandle()
            self._cam = None
            return {"status": "error", "detail": f"StartGrabbing failed: 0x{ret:x}"}

        # Clear old live images
        if self._live_dir and os.path.isdir(self._live_dir):
            for fname in os.listdir(self._live_dir):
                if fname.startswith("raw_") or fname.startswith("result_"):
                    try:
                        os.remove(os.path.join(self._live_dir, fname))
                    except OSError:
                        pass

        # Start worker thread
        self._running = True
        self._total_frames = 0
        self._start_time = time.time()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

        logger.info("Camera acquisition started.")
        return {"status": "started"}

    def stop(self) -> dict:
        """Stop grabbing, join worker thread, close device."""
        self._running = False

        if self._worker_thread is not None:
            self._worker_thread.join(timeout=5.0)
            self._worker_thread = None

        if self._cam is not None and _sdk_available:
            try:
                self._cam.MV_CC_StopGrabbing()
                self._cam.MV_CC_CloseDevice()
                self._cam.MV_CC_DestroyHandle()
            except Exception:
                logger.exception("Error during camera disconnect.")
            self._cam = None

        # Clear frame queue
        with self._frame_lock:
            self._frame_queue.clear()

        logger.info("Camera acquisition stopped.")
        return {"status": "stopped"}

    def is_active(self) -> bool:
        """Return True if the camera is currently acquiring."""
        return self._running

    def get_status(self) -> dict:
        """Return current camera status dict."""
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        return {
            "active": self._running,
            "total_frames": self._total_frames,
            "elapsed_seconds": round(elapsed, 1),
            "effective_fps": round(self._total_frames / max(elapsed, 0.001), 2),
        }

    def finalize(self) -> None:
        """Stop if running + finalize SDK. Call on app shutdown."""
        if self._running:
            self.stop()
        if _sdk_available:
            try:
                MvCamera.MV_CC_Finalize()
            except Exception:
                logger.exception("Error during MV_CC_Finalize.")


# Module-level singleton
camera_controller = CameraController()
