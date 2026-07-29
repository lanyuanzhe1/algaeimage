# 样机演示实时监测双栏展示 + 一键启动 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 V2 新增 `/detect/live` 页面，点击按钮一键启动海康相机采集，左侧实时显示原始图、右侧显示 YOLO 标注图，2s 轮询刷新。

**Architecture:** 相机 SDK 集成进 backend 进程（worker 线程消费帧 → pipeline.run() → 存 PNG 到 static/live/ → stream_state 存 URL）。前端独立路由，通过 `/detect/latest` 轮询拿图片 URL + 元数据。

**Tech Stack:** FastAPI + Python threading + Vue3 Composition API + Element Plus + Pinia

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `shared/schemas.py` | 修改 | LatestResult 加 raw_image_url / result_image_url |
| `backend/app/services/stream_state.py` | 修改 | add_result 存储 image URLs |
| `backend/app/services/camera.py` | **新建** | CameraController 封装 SDK + worker 线程 |
| `backend/app/routes.py` | 修改 | 新增 /stream/start, /stream/stop, 修改 /detect/latest |
| `backend/app/main.py` | 修改 | lifespan 初始化 camera_controller, 挂载 static/live |
| `frontend/src/api/index.js` | 修改 | 新增 startStream / stopStream |
| `frontend/src/stores/detect.js` | 修改 | 删除 toggleLiveMode, 新增 startStream/stopStream, 重命名 |
| `frontend/src/router/index.js` | 修改 | 注册 /detect/live |
| `frontend/src/views/LiveMonitor.vue` | **新建** | 双栏实时监测页面 |
| `frontend/src/App.vue` | 修改 | 删除 el-switch, 加实时监测菜单项 |
| `frontend/src/views/HistoryPage.vue` | 修改 | onMounted 自动轮询新记录 |

---

### Task 1: shared/schemas.py — LatestResult 新增图片 URL 字段

**Files:**
- Modify: `code/algae_image_v2/shared/schemas.py:99-107`

- [ ] **Step 1: 给 LatestResult 添加两个 Optional 字段**

```python
# 找到 LatestResult 类（约第 99 行），替换为：
class LatestResult(BaseModel):
    """/detect/latest 返回的单条摘要 (不含 base64 图片，保持轻量)"""
    id: str
    filename: str
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    processing_time_ms: float
    raw_image_url: Optional[str] = None       # 原始采集图 URL，手动上传时为 null
    result_image_url: Optional[str] = None    # YOLO 标注图 URL，手动上传时为 null
```

- [ ] **Step 2: 运行 API 测试确认向后兼容**

```bash
cd e:/code/algaeimage/code/algae_image_v2
python -m pytest tests/test_api.py -v -k "latest"
```
Expected: PASS（Optional 字段默认 None，旧测试不受影响）

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/shared/schemas.py
git commit -m "feat: add raw_image_url + result_image_url to LatestResult schema"
```

---

### Task 2: stream_state.py — add_result 存储 image URLs

**Files:**
- Modify: `code/algae_image_v2/backend/app/services/stream_state.py:25-34`

- [ ] **Step 1: add_result 接受额外关键字参数**

将 `add_result` 方法改为：

```python
def add_result(self, result: dict, raw_image_url: str = "", result_image_url: str = "") -> None:
    """Push a detection result into the buffer."""
    with self._lock:
        if self._start_time is None:
            self._start_time = time.time()
        self._total_frames += 1
        result["raw_image_url"] = raw_image_url
        result["result_image_url"] = result_image_url
        self._results.insert(0, result)
        if len(self._results) > MAX_RESULTS:
            self._results = self._results[:MAX_RESULTS]
```

- [ ] **Step 2: 确认现有调用兼容（routes.py 中两处 add_result 不传 image_url 时默认空字符串）**

无需修改 routes.py 现有代码——默认参数 `raw_image_url=""` 和 `result_image_url=""` 保证向后兼容。

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/backend/app/services/stream_state.py
git commit -m "feat: stream_state.add_result supports raw/result image URLs"
```

---

### Task 3: camera.py — 新建相机控制模块

**Files:**
- Create: `code/algae_image_v2/backend/app/services/camera.py`

- [ ] **Step 1: 创建 camera.py，封装 SDK 初始化 + 回调 + worker 线程**

```python
"""Camera controller — MVS SDK integration for MV-CA013-20GC.

Encapsulates SDK init, frame callback, and a worker thread that
feeds frames into the detection pipeline and saves live images.
"""
import ctypes
import os
import sys
import threading
import time
from ctypes import POINTER, byref, cast, c_void_p, memset

import cv2
import numpy as np

# ═══════════════════════════════════════════════════════
# MVS SDK path setup (must happen BEFORE importing SDK)
# ═══════════════════════════════════════════════════════
_MVS_DIR = r"A:\Program Files\MVS"
_MVIMP_DIR = os.path.join(_MVS_DIR, "Development", "Samples", "Python", "MvImport")
_DLL_DIR = r"C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64"

if _MVIMP_DIR not in sys.path:
    sys.path.insert(0, _MVIMP_DIR)
os.environ["PATH"] = _DLL_DIR + ";" + os.environ.get("PATH", "")
try:
    os.add_dll_directory(_DLL_DIR)
except AttributeError:
    pass  # Python < 3.8

from MvCameraControl_class import (
    MvCamera, MV_CC_DEVICE_INFO_LIST, MV_CC_DEVICE_INFO,
    MV_FRAME_OUT, MV_CC_HB_DECODE_PARAM, MV_CC_PIXEL_CONVERT_PARAM_EX,
    MV_ACCESS_Exclusive, MV_TRIGGER_MODE_OFF,
    MV_GIGE_DEVICE, MV_USB_DEVICE, MV_GENTL_GIGE_DEVICE,
    get_platform_functype,
    PixelType_Gvsp_RGB8_Packed,
)

_PIXEL_TYPES_HB = {
    0x02180001, 0x02180003, 0x02180005, 0x02180007,
    0x02180009, 0x0218000B, 0x0218000D, 0x0218000F, 0x02180011,
    0x02180013, 0x02180015,
    0x02280001, 0x02280003, 0x02280005, 0x02280007,
    0x02280009, 0x0228000B, 0x0228000D, 0x0228000F,
    0x02280011, 0x02280013,
}


class CameraController:
    """Manages MVS SDK camera lifecycle and frame processing."""

    def __init__(self):
        self._cam = None
        self._dev_info = None
        self._frame_queue: list = []
        self._frame_lock = threading.Lock()
        self._running = False
        self._worker_thread = None
        self._frame_count = 0
        self._start_time: float | None = None
        self._pipeline = None               # set by configure()
        self._live_dir = ""                 # set by configure()
        self._max_images = 50               # keep last 50 frames
        self._sdk_initialized = False
        self._init_sdk()

    # ── SDK lifecycle ─────────────────────────────────

    def _init_sdk(self):
        """Initialize SDK and enumerate devices (does not open)."""
        MvCamera.MV_CC_Initialize()
        version = MvCamera.MV_CC_GetSDKVersion()
        print(f"[Camera] SDK version: 0x{version:x}")

        deviceList = MV_CC_DEVICE_INFO_LIST()
        tlayer = MV_GIGE_DEVICE | MV_USB_DEVICE
        ret = MvCamera.MV_CC_EnumDevices(tlayer, deviceList)
        if ret != 0 or deviceList.nDeviceNum == 0:
            print("[Camera] WARNING: No camera found. Start will fail until camera is connected.")
            self._sdk_initialized = False
            return

        print(f"[Camera] Found {deviceList.nDeviceNum} device(s)")
        self._dev_info = cast(deviceList.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents
        self._sdk_initialized = True

    def configure(self, pipeline, live_dir: str):
        """Set the pipeline runner and live image output directory."""
        self._pipeline = pipeline
        self._live_dir = live_dir
        os.makedirs(live_dir, exist_ok=True)

    # ── Frame decode ──────────────────────────────────

    def _decode_frame(self, stFrame):
        """HB decode + pixel convert → RGB numpy array, or None on failure."""
        w, h = stFrame.stFrameInfo.nWidth, stFrame.stFrameInfo.nHeight
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

    # ── SDK callback ──────────────────────────────────

    def _make_callback(self):
        _functype = get_platform_functype()
        _FrameCallbackType = _functype(None, POINTER(MV_FRAME_OUT), c_void_p, ctypes.c_bool)

        controller_self = self  # capture for closure

        def _image_callback(pstFrame, pUser, bAutoFree):
            stFrame = cast(pstFrame, POINTER(MV_FRAME_OUT)).contents
            if not stFrame:
                return
            rgb = controller_self._decode_frame(stFrame)
            if rgb is not None:
                with controller_self._frame_lock:
                    controller_self._frame_queue.append(rgb)
            if not bAutoFree and pUser is not None:
                controller_self._cam.MV_CC_FreeImageBuffer(stFrame)

        return _FrameCallbackType(_image_callback)

    # ── Worker thread ─────────────────────────────────

    def _worker(self):
        """Consume frame queue, run pipeline, save images, push to stream_state."""
        from backend.app.services.stream_state import stream_state
        import json

        while self._running:
            with self._frame_lock:
                if self._frame_queue:
                    frame = self._frame_queue[-1]  # take latest
                    self._frame_queue.clear()
                else:
                    frame = None

            if frame is None:
                time.sleep(0.05)
                continue

            self._frame_count += 1
            frame_id = f"{self._frame_count:06d}"

            try:
                # Save raw frame
                raw_path = os.path.join(self._live_dir, f"raw_{frame_id}.png")
                cv2.imwrite(raw_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

                # Save frame as temp file for pipeline (pipeline.run() reads from disk)
                temp_path = os.path.join(self._live_dir, f"_temp_{frame_id}.png")
                cv2.imwrite(temp_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

                # Run pipeline
                result = self._pipeline.run(temp_path)

                # Save YOLO result image
                result_path = os.path.join(self._live_dir, f"result_{frame_id}.png")
                cv2.imwrite(result_path, cv2.cvtColor(result["result_image"], cv2.COLOR_RGB2BGR))

                # Clean up temp
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

                # Build detection items
                det_items = [
                    {
                        "class_id": d["class_id"],
                        "class_name": d["class_name"],
                        "class_name_zh": d.get("class_name_zh", d["class_name"]),
                        "confidence": round(d["confidence"], 4),
                        "bbox": [round(v, 1) for v in d["bbox"]],
                        "risk_level": d.get("risk_level", "low"),
                    }
                    for d in result["detections"]
                ]

                # Overall risk
                risks = [d["risk_level"] for d in result["detections"]]
                if "high" in risks:
                    risk = "high"
                elif "medium" in risks:
                    risk = "medium"
                elif risks:
                    risk = "low"
                else:
                    risk = None

                # Push to stream state
                stream_state.add_result(
                    {
                        "id": f"live_{frame_id}",
                        "filename": f"live_{frame_id}",
                        "detections": det_items,
                        "q_score": round(float(result["q_score"]), 4),
                        "risk_level": risk,
                        "processing_time_ms": result["processing_time_ms"],
                    },
                    raw_image_url=f"/static/live/raw_{frame_id}.png",
                    result_image_url=f"/static/live/result_{frame_id}.png",
                )

                print(f"[Camera] frame {frame_id}: {len(result['detections'])} dets, "
                      f"risk={risk}, {result['processing_time_ms']:.0f}ms")

            except Exception as e:
                print(f"[Camera] ERROR processing frame {frame_id}: {e}")
                import traceback
                traceback.print_exc()

            # Prune old images
            self._prune_images()

    def _prune_images(self):
        """Keep only the last _max_images frames worth of images on disk."""
        import glob as _glob
        raw_files = sorted(_glob.glob(os.path.join(self._live_dir, "raw_*.png")))
        result_files = sorted(_glob.glob(os.path.join(self._live_dir, "result_*.png")))
        all_files = raw_files + result_files
        # Each frame has 2 files; keep 2 * _max_images files
        keep = self._max_images * 2
        if len(all_files) > keep:
            for f in all_files[:-keep]:
                try:
                    os.remove(f)
                except OSError:
                    pass

    # ── Public API ────────────────────────────────────

    def start(self) -> dict:
        """Start camera acquisition. Returns {status, detail}."""
        if not self._sdk_initialized or self._dev_info is None:
            return {"status": "error", "detail": "相机未连接，请检查 GigE 连接和供电"}
        if self._running:
            return {"status": "error", "detail": "采集已在运行中"}
        if self._pipeline is None:
            return {"status": "error", "detail": "Pipeline 未就绪"}

        try:
            self._cam = MvCamera()
            ret = self._cam.MV_CC_CreateHandle(self._dev_info)
            if ret != 0:
                return {"status": "error", "detail": f"CreateHandle 失败: 0x{ret:x}"}

            ret = self._cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                self._cam.MV_CC_DestroyHandle()
                self._cam = None
                if ret == 0x80000203:
                    return {"status": "error", "detail": "相机被占用，请关闭 MVS 客户端后重试"}
                return {"status": "error", "detail": f"OpenDevice 失败: 0x{ret:x}"}

            # GigE optimisation
            if self._dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
                pkt = self._cam.MV_CC_GetOptimalPacketSize()
                if pkt > 0:
                    self._cam.MV_CC_SetIntValue("GevSCPSPacketSize", pkt)

            self._cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)

            # Register callback
            callback = self._make_callback()
            ret = self._cam.MV_CC_RegisterImageCallBackEx2(callback, ctypes.py_object(None), True)
            if ret != 0:
                self._cam.MV_CC_CloseDevice()
                self._cam.MV_CC_DestroyHandle()
                self._cam = None
                return {"status": "error", "detail": f"RegisterImageCallBackEx2 失败: 0x{ret:x}"}

            # Start grabbing
            ret = self._cam.MV_CC_StartGrabbing()
            if ret != 0:
                self._cam.MV_CC_CloseDevice()
                self._cam.MV_CC_DestroyHandle()
                self._cam = None
                return {"status": "error", "detail": f"StartGrabbing 失败: 0x{ret:x}"}

            # Clear old live images
            import glob as _glob
            for f in _glob.glob(os.path.join(self._live_dir, "*.png")):
                try:
                    os.remove(f)
                except OSError:
                    pass

            # Reset counters
            self._frame_count = 0
            self._start_time = time.time()
            self._running = True

            # Spawn worker thread
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

            print("[Camera] Acquisition started")
            return {"status": "started"}

        except Exception as e:
            print(f"[Camera] Start error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "detail": str(e)}

    def stop(self) -> dict:
        """Stop camera acquisition."""
        self._running = False

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)

        if self._cam:
            try:
                self._cam.MV_CC_StopGrabbing()
                self._cam.MV_CC_CloseDevice()
                self._cam.MV_CC_DestroyHandle()
            except Exception as e:
                print(f"[Camera] Stop cleanup error: {e}")
            self._cam = None

        print("[Camera] Acquisition stopped")
        return {"status": "stopped"}

    def is_active(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        return {
            "active": self._running,
            "total_frames": self._frame_count,
            "elapsed_seconds": round(elapsed, 1),
            "effective_fps": round(self._frame_count / max(elapsed, 0.001), 2),
        }

    def finalize(self):
        """Clean shutdown: stop acquisition + finalize SDK."""
        if self._running:
            self.stop()
        MvCamera.MV_CC_Finalize()


# Module-level singleton
camera_controller = CameraController()
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/backend/app/services/camera.py
git commit -m "feat: add CameraController — MVS SDK integration with worker thread"
```

---

### Task 4: routes.py — 新增 /stream/start, /stream/stop, 修改 /detect/latest

**Files:**
- Modify: `code/algae_image_v2/backend/app/routes.py`

- [ ] **Step 1: 在 routes.py 顶部 import camera_controller**

在第 19 行（`from .services.stream_state import stream_state` 之后）添加：

```python
from .services.camera import camera_controller
```

- [ ] **Step 2: 修改 /detect/latest 端点，返回 image_url 字段**

找到 `get_latest_results` 函数（约第 296 行），替换 `LatestResult` 构造部分：

```python
@router.get("/detect/latest", response_model=LatestResultsResponse)
async def get_latest_results(n: int = Query(default=10, ge=1, le=50)):
    """Return the N most recent detection results (for frontend polling)."""
    raw = stream_state.get_latest(n)
    results = [
        LatestResult(
            id=r["id"],
            filename=r["filename"],
            detections=[DetectionItem(**d) for d in r["detections"]],
            q_score=r["q_score"],
            risk_level=r.get("risk_level"),
            processing_time_ms=r["processing_time_ms"],
            raw_image_url=r.get("raw_image_url", ""),
            result_image_url=r.get("result_image_url", ""),
        )
        for r in raw
    ]
    return LatestResultsResponse(results=results, count=len(results))
```

- [ ] **Step 3: 新增 POST /detect/stream/start 端点**

在 `/detect/stream-status` 端点之后、router 定义结束之前添加：

```python
@router.post("/detect/stream/start")
async def stream_start():
    """Start live camera acquisition."""
    if camera_controller is None:
        raise HTTPException(status_code=503, detail="Camera SDK not available on this system")
    result = camera_controller.start()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))
    return result


@router.post("/detect/stream/stop")
async def stream_stop():
    """Stop live camera acquisition."""
    if camera_controller is None:
        raise HTTPException(status_code=503, detail="Camera SDK not available")
    return camera_controller.stop()
```

- [ ] **Step 4: 运行 API 测试**

```bash
cd e:/code/algaeimage/code/algae_image_v2
python -m pytest tests/test_api.py -v
```
Expected: 7 passed（新增端点不影响现有测试）

- [ ] **Step 5: Commit**

```bash
git add code/algae_image_v2/backend/app/routes.py
git commit -m "feat: add /stream/start, /stream/stop endpoints + image URLs in /latest"
```

---

### Task 5: main.py — lifespan 初始化 camera_controller + 挂载 static/live

**Files:**
- Modify: `code/algae_image_v2/backend/app/main.py`

- [ ] **Step 1: lifespan 中添加 camera_controller 初始化**

找到 lifespan 函数的 yield 前（约第 39 行），在 `pipeline_runner = ...` 之后添加：

```python
    # Init camera controller (lazy — won't open device until /stream/start)
    try:
        from backend.app.services.camera import camera_controller
        camera_controller.configure(pipeline_runner, os.path.join(RESULT_DIR, "live"))
        app.state.camera_controller = camera_controller
        print("[Startup] Camera controller ready")
    except Exception as e:
        print(f"[Startup] Camera SDK not available (non-Windows or MVS not installed): {e}")
        app.state.camera_controller = None
```

在 yield 之后（第 41 行 `pipeline_runner = None` 之后）添加：

```python
    # Shutdown camera if running
    if app.state.camera_controller:
        app.state.camera_controller.finalize()
        print("[Shutdown] Camera controller released")
```

- [ ] **Step 2: 确认 static/live 目录创建 + StaticFiles 挂载**

在 `os.makedirs(RESULT_DIR, exist_ok=True)`（第 66 行）之前添加：

```python
_live_dir = os.path.join(RESULT_DIR, "live")
os.makedirs(_live_dir, exist_ok=True)
```

在 `app.mount("/static/results", ...)`（第 67 行）之后添加：

```python
app.mount("/static/live", StaticFiles(directory=_live_dir), name="live")
```

- [ ] **Step 3: 运行 API 测试确认无回归**

```bash
cd e:/code/algaeimage/code/algae_image_v2
python -m pytest tests/test_api.py -v
```
Expected: 7 passed

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v2/backend/app/main.py
git commit -m "feat: init camera controller in lifespan + mount /static/live"
```

---

### Task 6: frontend API 层 — 新增 startStream / stopStream

**Files:**
- Modify: `code/algae_image_v2/frontend/src/api/index.js`

- [ ] **Step 1: 在 Live Stream 区块添加两个新函数**

找到 `// ─── Live Stream ───` 注释块（约第 44 行），在文件末尾添加：

```javascript
/** Start camera acquisition */
export function startStream() {
  return api.post('/detect/stream/start')
}

/** Stop camera acquisition */
export function stopStream() {
  return api.post('/detect/stream/stop')
}
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/frontend/src/api/index.js
git commit -m "feat: add startStream / stopStream API functions"
```

---

### Task 7: Pinia Store 重构 — 删除 toggleLiveMode, 新增 stream 控制

**Files:**
- Modify: `code/algae_image_v2/frontend/src/stores/detect.js`

- [ ] **Step 1: 重写 detect.js**

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLatestResults, getStreamStatus, startStream, stopStream } from '@/api'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = ref(null)
  const isProcessing = ref(false)
  const error = ref(null)

  // ── Live stream state ──────────────────────────────────────
  const isStreaming = ref(false)
  const liveResults = ref([])
  const streamStatus = ref({ active: false, total_frames: 0, effective_fps: 0, elapsed_seconds: 0 })
  let _pollTimer = null

  function setResult(result) {
    currentResult.value = result
    error.value = null
    liveResults.value.unshift(result)
    if (liveResults.value.length > 50) liveResults.value.length = 50
  }

  function clearResult() {
    currentResult.value = null
    error.value = null
  }

  function setError(msg) {
    error.value = msg
    currentResult.value = null
  }

  // ── Stream control ────────────────────────────────────────

  async function start() {
    const res = await startStream()
    if (res.data.status === 'started') {
      isStreaming.value = true
    }
    return res.data
  }

  async function stop() {
    const res = await stopStream()
    isStreaming.value = false
    return res.data
  }

  // ── Polling ───────────────────────────────────────────────

  function startStreamPolling() {
    _pollTimer = setInterval(async () => {
      try {
        const [rRes, sRes] = await Promise.all([
          getLatestResults(5),
          getStreamStatus(),
        ])
        liveResults.value = rRes.data.results || []
        streamStatus.value = sRes.data
        if (!sRes.data.active) {
          isStreaming.value = false
        }
      } catch (_e) { /* backend may be starting */ }
    }, 2000)
  }

  function stopStreamPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  }

  return {
    currentResult, isProcessing, error, setResult, clearResult, setError,
    isStreaming, liveResults, streamStatus,
    start, stop, startStreamPolling, stopStreamPolling,
  }
})
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/frontend/src/stores/detect.js
git commit -m "refactor: replace toggleLiveMode with start/stop + startStreamPolling/stopStreamPolling"
```

---

### Task 8: Router — 注册 /detect/live

**Files:**
- Modify: `code/algae_image_v2/frontend/src/router/index.js`

- [ ] **Step 1: 在 routes 数组中 `/detect` 之后添加新路由**

```javascript
  {
    path: '/detect',
    name: 'detect',
    component: () => import('@/views/DetectPage.vue'),
  },
  {
    path: '/detect/live',
    name: 'liveMonitor',
    component: () => import('@/views/LiveMonitor.vue'),
  },
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/frontend/src/router/index.js
git commit -m "feat: register /detect/live route"
```

---

### Task 9: LiveMonitor.vue — 新建双栏实时监测页面

**Files:**
- Create: `code/algae_image_v2/frontend/src/views/LiveMonitor.vue`

- [ ] **Step 1: 创建 LiveMonitor.vue**

```vue
<template>
  <div class="live-monitor" style="max-width:1200px; margin:0 auto">
    <!-- Control bar -->
    <div class="control-bar">
      <el-button
        type="primary"
        size="large"
        :loading="state === 'starting'"
        :disabled="state === 'running'"
        @click="handleStart"
      >
        开始采集
      </el-button>
      <el-button
        type="danger"
        size="large"
        :loading="state === 'stopping'"
        :disabled="state !== 'running'"
        @click="handleStop"
      >
        停止
      </el-button>
      <span class="stream-indicator" :class="state">
        <span class="dot"></span>
        {{ stateText }}
      </span>
      <span v-if="store.streamStatus.total_frames" class="stream-stats">
        {{ store.streamStatus.total_frames }}帧
        {{ store.streamStatus.effective_fps?.toFixed(1) }}fps
      </span>
    </div>

    <!-- Error -->
    <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable
              style="margin-bottom:16px" @close="errorMsg = null" />

    <!-- Dual panel -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="12">
        <el-card shadow="never" class="image-panel">
          <template #header>
            <span>原始采集图</span>
            <span v-if="rawUrl" style="font-size:12px;color:#999;float:right">
              {{ currentFilename }}
            </span>
          </template>
          <div class="image-wrapper">
            <img v-if="rawUrl" :key="rawUrl" :src="rawUrl" alt="raw" class="live-image" />
            <div v-else class="placeholder">
              <el-icon :size="48"><VideoCamera /></el-icon>
              <p>{{ placeholderText }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="image-panel">
          <template #header>
            <span>YOLO 检测结果</span>
            <span v-if="resultUrl" style="font-size:12px;color:#999;float:right">
              {{ detectionSummary }}
            </span>
          </template>
          <div class="image-wrapper">
            <img v-if="resultUrl" :key="resultUrl" :src="resultUrl" alt="result" class="live-image" />
            <div v-else class="placeholder">
              <el-icon :size="48"><PictureFilled /></el-icon>
              <p>{{ placeholderText }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Stats + Results -->
    <StatsCards v-if="statsCards.length" :cards="statsCards" style="margin-bottom:16px" />
    <ResultTable
      v-for="(lr, i) in store.liveResults.slice(0, 5)"
      :key="lr.id"
      :detections="lr.detections"
      :style="i === 0 ? '' : 'margin-top:12px;opacity:0.55'"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useDetectStore } from '@/stores/detect'
import StatsCards from '@/components/StatsCards.vue'
import ResultTable from '@/components/ResultTable.vue'

const store = useDetectStore()

// State machine: idle | starting | running | stopping | error
const state = ref('idle')
const errorMsg = ref(null)

// Computed
const stateText = computed(() => ({
  idle: '等待开始',
  starting: '正在启动...',
  running: '采集中',
  stopping: '正在停止...',
  error: '异常',
})[state.value])

const placeholderText = computed(() => {
  if (state.value === 'idle') return '点击「开始采集」启动'
  if (state.value === 'starting') return '正在启动相机...'
  if (state.value === 'error') return errorMsg.value || '采集异常'
  return '等待图像...'
})

const latest = computed(() => store.liveResults[0] || null)
const rawUrl = computed(() => latest.value?.raw_image_url || null)
const resultUrl = computed(() => latest.value?.result_image_url || null)
const currentFilename = computed(() => latest.value?.filename || '')
const detectionSummary = computed(() => {
  if (!latest.value) return ''
  const n = latest.value.detections?.length || 0
  const risk = latest.value.risk_level
  return `${n} 个检出 · ${risk === 'high' ? '高危' : risk === 'medium' ? '中危' : risk === 'low' ? '低危' : '无'}`
})

const statsCards = computed(() => {
  if (!store.liveResults.length) return []
  const lv = latest.value
  const allDets = store.liveResults.flatMap(r => r.detections || [])
  return [
    { label: '检测帧数', value: store.streamStatus.total_frames, sub: '已处理' },
    { label: '最新风险', value: lv?.risk_level || '无', sub: '风险等级',
      color: lv?.risk_level === 'high' ? '#dc2626' : lv?.risk_level === 'medium' ? '#f59e0b' : '#16a34a' },
    { label: '最新 Q 分', value: lv?.q_score?.toFixed(3) || '--', sub: '质量评分' },
    { label: '累计检出', value: allDets.length, sub: '藻类个体' },
    { label: '有效 FPS', value: store.streamStatus.effective_fps?.toFixed(1) || '0.0', sub: '实时帧率' },
  ]
})

// Actions
async function handleStart() {
  state.value = 'starting'
  errorMsg.value = null
  try {
    const res = await store.start()
    if (res.status === 'started') {
      state.value = 'running'
      store.startStreamPolling()
    } else {
      state.value = 'error'
      errorMsg.value = res.detail || '启动失败'
    }
  } catch (e) {
    state.value = 'error'
    errorMsg.value = e.response?.data?.detail || '启动失败，请检查相机连接'
  }
}

async function handleStop() {
  state.value = 'stopping'
  try {
    store.stopStreamPolling()
    await store.stop()
    state.value = 'idle'
  } catch (e) {
    state.value = 'idle'
  }
}

// Watch for stream going inactive externally
watch(() => store.streamStatus.active, (active) => {
  if (!active && state.value === 'running') {
    state.value = 'idle'
    store.stopStreamPolling()
    errorMsg.value = '采集已中断，请检查相机连接'
  }
})

onUnmounted(() => {
  store.stopStreamPolling()
})
</script>

<style scoped>
.control-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.stream-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}
.stream-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}
.stream-indicator.running .dot {
  background: #67c23a;
  animation: pulse 1.5s infinite;
}
.stream-indicator.error .dot {
  background: #dc2626;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.stream-stats {
  font-size: 12px;
  color: #67c23a;
  margin-left: auto;
}
.image-panel {
  height: 100%;
}
.image-panel :deep(.el-card__body) {
  padding: 0;
}
.image-wrapper {
  width: 100%;
  aspect-ratio: 4/3;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.live-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.placeholder {
  text-align: center;
  color: #666;
}
.placeholder p {
  margin-top: 8px;
  font-size: 13px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/frontend/src/views/LiveMonitor.vue
git commit -m "feat: add LiveMonitor page — dual-panel real-time display"
```

---

### Task 10: App.vue — 删除 el-switch, 加实时监测菜单项

**Files:**
- Modify: `code/algae_image_v2/frontend/src/App.vue`

- [ ] **Step 1: 删除导航栏 live-toggle 区块**

找到 `<div class="live-toggle">` 代码块（第 28-38 行），删除整个区块：

```html
        <div class="live-toggle">
          <el-switch
            v-model="store.liveMode"
            @change="store.toggleLiveMode"
            active-text="实时监测"
            size="large"
          />
          <span v-if="store.liveMode" class="live-badge">
            {{ store.streamStatus.total_frames }}帧 {{ store.streamStatus.effective_fps?.toFixed(1) }}fps
          </span>
        </div>
```

- [ ] **Step 2: 新增菜单项**

在 `<el-menu-item index="/detect">检测工具</el-menu-item>` 之后添加：

```html
          <el-menu-item index="/detect/live">实时监测</el-menu-item>
```

把原菜单项的 text 改为 "手动检测"：

```html
          <el-menu-item index="/detect">手动检测</el-menu-item>
```

- [ ] **Step 3: 简化 `<script setup>`**

删除不再需要的 store import（如果 `liveMode` 和 `streamStatus` 不再使用）。当前的 import 可以保留（`useDetectStore` 仍被其他组件通过 router-view 使用），但删除 nav-bar 绑定的 `store.liveMode` 后，store 不再在 template 中被 App.vue 直接引用。可以把 import 精简为按需。

当前 App.vue 的 script 部分改为：

```javascript
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.path)

function handleSelect(index) {
  router.push(index)
}
</script>
```

并删除 CSS 中的 `.live-toggle` 和 `.live-badge` 样式（第 101-113 行）。

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v2/frontend/src/App.vue
git commit -m "fix: remove broken el-switch, add /detect/live nav item"
```

---

### Task 11: HistoryPage.vue — 自动轮询新记录

**Files:**
- Modify: `code/algae_image_v2/frontend/src/views/HistoryPage.vue`

- [ ] **Step 1: 添加自动轮询逻辑**

在 `<script setup>` 中，`onMounted(fetchHistory)` 之后添加轮询逻辑。将当前的 `onMounted(fetchHistory)` 替换为：

```javascript
import { ref, onMounted, onUnmounted } from 'vue'

// ... existing code ...

let _historyTimer = null

onMounted(() => {
  fetchHistory()
  // Auto-poll: check for new records every 3s when on page 1
  _historyTimer = setInterval(async () => {
    if (page.value !== 1) return  // only auto-refresh on first page
    try {
      const res = await getHistory(1, limit)
      const newItems = res.data.items || []
      // If we have records and the latest ID differs, prepend new ones
      if (newItems.length && items.value.length) {
        const existingIds = new Set(items.value.map(i => i.id))
        const fresh = newItems.filter(i => !existingIds.has(i.id))
        if (fresh.length) {
          items.value = [...fresh, ...items.value].slice(0, limit * 5) // keep reasonable cap
        }
      } else if (newItems.length) {
        items.value = newItems
      }
    } catch (_e) { /* silently ignore poll errors */ }
  }, 3000)
})

onUnmounted(() => {
  if (_historyTimer) { clearInterval(_historyTimer); _historyTimer = null }
})
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/frontend/src/views/HistoryPage.vue
git commit -m "feat: auto-poll history page for new records every 3s"
```

---

### Task 12: 集成验证 — 构建前端 + 启动后端

**Files:**
- None (验证步骤)

- [ ] **Step 1: 构建前端**

```bash
cd e:/code/algaeimage/code/algae_image_v2/frontend
npm run build
```
Expected: `✓ built in Xs`

- [ ] **Step 2: 启动后端确认无 import 错误**

```bash
cd e:/code/algaeimage/code/algae_image_v2
A:/Anaconda_envs/envs/ican/python.exe -c "from backend.app.services.camera import camera_controller; print('Camera module OK')"
```
Expected: `Camera module OK` 或 SDK warning（非 Windows 环境）

- [ ] **Step 3: 运行全量 API 测试**

```bash
cd e:/code/algaeimage/code/algae_image_v2
python -m pytest tests/test_api.py -v
```
Expected: 7 passed

- [ ] **Step 4: 强制添加前端 dist/ 更新到 git（dist/ 在 .gitignore 中）**

```bash
cd e:/code/algaeimage/code/algae_image_v2
git add -f frontend/dist/
git commit -m "build: update frontend dist for live monitor release"
```

- [ ] **Step 5: 最终提交（如有遗漏文件）**

```bash
git status
# 确认所有改动已提交
```

---

## 实施顺序

```
Task 1 (schemas) → Task 2 (stream_state) → Task 3 (camera.py)
    → Task 4 (routes) → Task 5 (main.py)
    → Task 6 (api) → Task 7 (store) → Task 8 (router)
    → Task 9 (LiveMonitor.vue) → Task 10 (App.vue) → Task 11 (HistoryPage)
    → Task 12 (build + verify)
```

所有 Task 按依赖顺序串行。Task 1-5 后端，Task 6-11 前端，Task 12 集成验证。
