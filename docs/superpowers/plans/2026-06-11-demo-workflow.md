# 样机演示流程 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建从相机/视频采集到前端实时展示的完整样机演示流程

**Architecture:** video_grabber.py (AVI 回放) → POST /api/v1/detect → stream_state (内存 buffer) → GET /detect/latest → DetectPage 2s 轮询

**Tech Stack:** Python 3.11, FastAPI, OpenCV, Vue3 + Element Plus + Axios

---

## 文件结构

```
code/algae_image_v2/
├── video_grabber.py                    # 新增: AVI 回放采集器
├── camera_grabber.py                   # 新增: SDK 采集器 (Phase 4)
├── backend/app/
│   ├── routes.py                       # 修改: 加 /detect/latest + /detect/stream-status
│   └── services/
│       ├── pipeline.py                 # 已有
│       └── stream_state.py             # 新增: 内存状态管理
├── shared/
│   └── schemas.py                      # 修改: 加 StreamStatusResponse, LatestResultsResponse
└── frontend/src/
    ├── api/index.js                    # 修改: 加 getLatestResults, getStreamStatus
    └── views/DetectPage.vue            # 修改: 加实时模式
```

---

### Task 1: video_grabber.py — AVI 回放采集器

**Files:**
- Create: `code/algae_image_v2/video_grabber.py`

- [ ] **Step 1: 写 video_grabber.py**

```python
"""Video grabber — read AVI frames and POST to detection backend.

Usage:
    python video_grabber.py video/Video_20260611215520245.avi
    python video_grabber.py video/Video_20260611215520245.avi --fps 5 --loop

Without camera hardware, this simulates the live acquisition flow:
AVI file → cv2 frame → POST /api/v1/detect/visualize → backend pipeline.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_FPS = 10  # target frames per second to send


def main():
    parser = argparse.ArgumentParser(description="AVI frame grabber → detection backend")
    parser.add_argument("video", help="Path to AVI file")
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS,
                        help=f"Target frames/sec to POST (default: {DEFAULT_FPS})")
    parser.add_argument("--loop", action="store_true",
                        help="Loop video continuously (for demo mode)")
    parser.add_argument("--once", action="store_true",
                        help="Send one frame and exit (quick smoke test)")
    parser.add_argument("--base-url", default=BASE_URL,
                        help=f"Backend base URL (default: {BASE_URL})")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"[INFO] Video: {video_path.name} | {w}x{h} | {source_fps:.1f} fps | {total_frames} frames")
    print(f"[INFO] Target send rate: {args.fps} fps")
    print(f"[INFO] Backend: {args.base_url}")

    interval = 1.0 / args.fps
    frame_idx = 0
    sent_count = 0
    fail_count = 0
    start_time = time.time()

    try:
        while True:
            if args.once and sent_count >= 1:
                break

            ret, frame = cap.read()
            if not ret:
                if args.loop:
                    print("[INFO] Video ended, looping...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx = 0
                    continue
                else:
                    print("[INFO] Video ended.")
                    break

            frame_idx += 1

            # Throttle to target fps
            elapsed = time.time() - start_time
            expected = frame_idx / args.fps
            if elapsed < expected:
                time.sleep(expected - elapsed)

            # Encode frame as JPEG bytes
            _, jpeg = cv2.imencode(".jpg", frame)
            files = {"file": (f"frame_{frame_idx:06d}.jpg", jpeg.tobytes(), "image/jpeg")}

            try:
                t0 = time.time()
                resp = requests.post(
                    f"{args.base_url}/detect/visualize",
                    files=files,
                    timeout=30,
                )
                dt = (time.time() - t0) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    n_det = len(data.get("detections", []))
                    risk = data.get("risk_level", "-")
                    sent_count += 1
                    print(f"  [{sent_count:04d}] frame={frame_idx} | "
                          f"{n_det} detections | risk={risk} | {dt:.0f}ms")
                else:
                    fail_count += 1
                    print(f"  [FAIL] frame={frame_idx} | HTTP {resp.status_code} | {resp.text[:80]}")

            except requests.exceptions.ConnectionError:
                print("[FATAL] Cannot connect to backend. Is it running?")
                print("        Start with: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000")
                sys.exit(1)
            except Exception as e:
                fail_count += 1
                print(f"  [ERR] frame={frame_idx} | {e}")

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")

    finally:
        cap.release()
        elapsed = time.time() - start_time
        print(f"\n[DONE] Sent={sent_count} Failed={fail_count} in {elapsed:.1f}s "
              f"({sent_count / max(elapsed, 0.1):.1f} fps effective)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test — 单帧发送**

```bash
# 先启动 backend (另一个终端)
cd e:/code/codex/code/algae_image_v2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# 单帧测试
A:/Anaconda_envs/envs/ican/python.exe video_grabber.py video/Video_20260611215520245.avi --once
```

Expected: 发送 1 帧，backend 返回检测结果 JSON，终端打印 `[0001]` 行。

- [ ] **Step 3: 完整回放测试**

```bash
A:/Anaconda_envs/envs/ican/python.exe video_grabber.py video/Video_20260611215520245.avi --fps 10 --loop
```

Expected: 持续发送帧，Ctrl+C 停止，打印汇总统计。

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v2/video_grabber.py
git commit -m "feat: add video_grabber.py — AVI frame replay to detection backend"
```

---

### Task 2: stream_state.py — 内存状态管理

**Files:**
- Create: `code/algae_image_v2/backend/app/services/stream_state.py`

- [ ] **Step 1: 写 stream_state.py**

```python
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

    def add_result(self, result: dict) -> None:
        """Push a detection result into the buffer."""
        with self._lock:
            if self._start_time is None:
                self._start_time = time.time()
            self._total_frames += 1
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
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/backend/app/services/stream_state.py
git commit -m "feat: add stream_state — in-memory buffer for live detection results"
```

---

### Task 3: Schemas — 新增响应模型

**Files:**
- Modify: `code/algae_image_v2/shared/schemas.py`

- [ ] **Step 1: 在 schemas.py 末尾追加两个新模型**

在 `shared/schemas.py` 末尾追加:

```python
class LatestResult(BaseModel):
    """/detect/latest 返回的单条摘要 (不含 base64 图片，保持轻量)"""
    id: str
    filename: str
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    processing_time_ms: float


class LatestResultsResponse(BaseModel):
    """GET /api/v1/detect/latest 响应"""
    results: list[LatestResult]
    count: int


class StreamStatusResponse(BaseModel):
    """GET /api/v1/detect/stream-status 响应"""
    active: bool
    total_frames: int
    buffer_size: int
    elapsed_seconds: float
    effective_fps: float
```

同步更新 `backend/app/schemas.py` 的 re-export:

```python
from shared.schemas import (  # noqa: F401, E402
    # ... existing imports ...
    LatestResult,
    LatestResultsResponse,
    StreamStatusResponse,
)
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/shared/schemas.py code/algae_image_v2/backend/app/schemas.py
git commit -m "feat: add LatestResultsResponse and StreamStatusResponse schemas"
```

---

### Task 4: Backend 新端点 — /detect/latest + /detect/stream-status

**Files:**
- Modify: `code/algae_image_v2/backend/app/routes.py`

- [ ] **Step 1: 在 routes.py 末尾追加两个端点**

在 `routes.py` 开头添加 import:

```python
from .services.stream_state import stream_state
from .schemas import (
    # ... existing imports ...
    LatestResult,
    LatestResultsResponse,
    StreamStatusResponse,
)
```

在 `POST /detect` 的返回语句之前，插入 stream_state 写入（找到 `return SingleDetectResponse(...)` ，在其上一行加）:

```python
    # Push to live stream buffer (before returning)
    stream_state.add_result({
        "id": file_id,
        "filename": file.filename or "unknown",
        "detections": [d.model_dump() for d in det_items],
        "q_score": round(result["q_score"], 4),
        "risk_level": risk,
        "processing_time_ms": result["processing_time_ms"],
    })
```

在文件末尾追加两个新端点:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# Live stream polling endpoints
# ═══════════════════════════════════════════════════════════════════════════════

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
            risk_level=r["risk_level"],
            processing_time_ms=r["processing_time_ms"],
        )
        for r in raw
    ]
    return LatestResultsResponse(results=results, count=len(results))


@router.get("/detect/stream-status", response_model=StreamStatusResponse)
async def get_stream_status():
    """Return live stream status (fps, frame count, uptime)."""
    return StreamStatusResponse(**stream_state.get_status())
```

- [ ] **Step 2: 手动测试端点**

```bash
# 启动 backend
cd e:/code/codex/code/algae_image_v2
A:/Anaconda_envs/envs/ican/python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# 测试 stream-status (初始为空)
curl -s http://localhost:8000/api/v1/detect/stream-status | python -m json.tool
# Expected: {"active": false, "total_frames": 0, ...}

# 用 video_grabber 发一帧
A:/Anaconda_envs/envs/ican/python.exe video_grabber.py video/Video_20260611215520245.avi --once

# 再次测试
curl -s http://localhost:8000/api/v1/detect/stream-status | python -m json.tool
# Expected: {"active": true, "total_frames": 1, ...}

curl -s http://localhost:8000/api/v1/detect/latest?n=3 | python -m json.tool
# Expected: {"results": [...], "count": 1}
```

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/backend/app/routes.py
git commit -m "feat: add /detect/latest and /detect/stream-status polling endpoints"
```

---

### Task 5: 前端 API 函数

**Files:**
- Modify: `code/algae_image_v2/frontend/src/api/index.js`

- [ ] **Step 1: 在 api/index.js 末尾追加两个函数**

```javascript
// ─── Live Stream ──────────────────────────────────────────────

/** Get the N most recent detection results */
export function getLatestResults(n = 10) {
  return api.get('/detect/latest', { params: { n } })
}

/** Get live stream status (fps, frame count, uptime) */
export function getStreamStatus() {
  return api.get('/detect/stream-status')
}
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/frontend/src/api/index.js
git commit -m "feat: add getLatestResults and getStreamStatus API functions"
```

---

### Task 6: DetectPage.vue — 实时模式

**Files:**
- Modify: `code/algae_image_v2/frontend/src/views/DetectPage.vue`

- [ ] **Step 1: 在 `<script setup>` 中添加实时模式逻辑**

在文件 `<script setup>` 部分添加以下代码（紧接在现有 imports 之后）:

```javascript
import { ref, onBeforeUnmount } from 'vue'
import { getLatestResults, getStreamStatus } from '../api/index.js'

// ── Live stream mode ──────────────────────────────────────────
const liveMode = ref(false)
const liveResults = ref([])
const streamStatus = ref({ active: false, total_frames: 0, effective_fps: 0, elapsed_seconds: 0 })
let _pollTimer = null

function toggleLiveMode() {
  liveMode.value = !liveMode.value
  if (liveMode.value) {
    startPolling()
  } else {
    stopPolling()
  }
}

function startPolling() {
  _pollTimer = setInterval(async () => {
    try {
      const [rRes, sRes] = await Promise.all([
        getLatestResults(10),
        getStreamStatus(),
      ])
      liveResults.value = rRes.data.results || []
      streamStatus.value = sRes.data
    } catch (e) {
      // Silently skip — backend may be starting up
    }
  }, 2000)
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer)
    _pollTimer = null
  }
}

onBeforeUnmount(() => stopPolling())
```

- [ ] **Step 2: 在模板顶部添加实时模式开关**

在 `</template>` 的 `<div class="detect-page">` 之后、`<el-card>` 之前插入:

```html
    <!-- Live mode toggle -->
    <el-card shadow="never" style="margin-bottom:20px">
      <el-switch
        v-model="liveMode"
        @change="toggleLiveMode"
        active-text="实时监测"
        inactive-text="手动检测"
      />
      <span v-if="liveMode" style="margin-left:16px;font-size:13px;color:#67c23a">
        运行中 | 已处理 {{ streamStatus.total_frames }} 帧 |
        有效 {{ streamStatus.effective_fps }} fps |
        运行 {{ streamStatus.elapsed_seconds }}s
      </span>
      <span v-else style="margin-left:16px;font-size:13px;color:#999">
        选择图片文件手动检测
      </span>
    </el-card>
```

- [ ] **Step 3: 在模板中将现有上传区和结果区用 v-if 包裹**

将现有的 `<el-card>` (上传区) 整个包裹:

```html
    <el-card v-if="!liveMode" shadow="never" style="margin-bottom:20px">
      <!-- 原有上传区内容不变 -->
    </el-card>
```

将 PipelineViz + StatsCards + ResultTable 部分改为支持 liveResults:

```html
    <!-- Live results -->
    <template v-if="liveMode && liveResults.length">
      <PipelineViz
        v-if="liveResults[0].steps"
        :steps="liveResults[0].steps"
      />
      <StatsCards :cards="liveStatsCards" style="margin-top:20px" />
      <ResultTable
        v-for="(r, i) in liveResults"
        :key="r.id"
        :detections="r.detections"
        :style="i === 0 ? '' : 'margin-top:12px; opacity:0.7'"
      />
    </template>
```

- [ ] **Step 4: 添加 liveStatsCards computed**

在 `<script setup>` 中添加:

```javascript
import { computed } from 'vue'

const liveStatsCards = computed(() => {
  if (!liveResults.value.length) return []
  const latest = liveResults.value[0]
  const allDets = liveResults.value.flatMap(r => r.detections)
  return [
    { label: '检测帧数', value: streamStatus.value.total_frames },
    { label: '最新风险', value: latest.risk_level || '无' },
    { label: '最新 Q 分', value: latest.q_score?.toFixed(3) || '--' },
    { label: '累计检出', value: allDets.length },
    { label: '有效 FPS', value: streamStatus.value.effective_fps.toFixed(1) },
  ]
})
```

- [ ] **Step 5: 构建验证**

```bash
cd e:/code/codex/code/algae_image_v2/frontend
npm run build
```

Expected: 构建成功，无报错。

- [ ] **Step 6: Commit**

```bash
git add code/algae_image_v2/frontend/src/views/DetectPage.vue
git commit -m "feat: add live monitoring mode to DetectPage with 2s polling"
```

---

### Task 7: 端到端集成测试

- [ ] **Step 1: 启动 backend**

```bash
cd e:/code/codex/code/algae_image_v2
A:/Anaconda_envs/envs/ican/python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 启动 video_grabber (循环模式)**

```bash
A:/Anaconda_envs/envs/ican/python.exe video_grabber.py video/Video_20260611215520245.avi --fps 5 --loop
```

- [ ] **Step 3: 打开前端验证实时更新**

```bash
# Dev server 或直接用 dist/ 静态文件
# 访问 http://localhost:5173/detect (Vite dev)
# 或 http://localhost:8000/app/ (FastAPI static)
```

Expected:
1. 打开"实时监测"开关 → 状态栏变绿，显示帧数/FPS
2. PipelineViz + ResultTable 每 2s 自动刷新
3. 关闭开关 → 回到手动上传模式
4. Ctrl+C 停止 video_grabber → 状态栏帧数停在最后

- [ ] **Step 4: Commit end-to-end verified**

```bash
git add -A
git commit -m "test: end-to-end live monitoring flow verified"
```

---

### Task 8: camera_grabber.py — SDK 采集器 (需相机硬件)

**Files:**
- Create: `code/algae_image_v2/camera_grabber.py`

> **注意:** 此任务需要相机硬件 MV-CA013-20GC 连接。如果相机不可用，先跳到 Phase 5 Docker。

- [ ] **Step 1: 写 camera_grabber.py**

```python
"""Camera grabber — MVS SDK direct frame capture → detection backend.

Requires: MV-CA013-20GC camera + MVS Python SDK (Development/ directory).
Without hardware, use video_grabber.py instead.

Usage:
    python camera_grabber.py
    python camera_grabber.py --fps 5 --duration 300

Architecture:
    SDK callback → numpy frame → JPEG encode → POST /api/v1/detect/visualize
"""
import argparse
import ctypes
import os
import sys
import time
from ctypes import POINTER, byref, cast, c_bool, c_void_p, memset

import cv2
import numpy as np
import requests

# ── SDK path setup ─────────────────────────────────────────────
_SDK_DIR = os.path.join(os.path.dirname(__file__), "..", "Development")
_MVIMP_DIR = os.path.join(_SDK_DIR, "Samples", "Python", "MvImport")
_DLL_DIR = os.path.join(_SDK_DIR, "Libraries", "win64")

if _MVIMP_DIR not in sys.path:
    sys.path.insert(0, _MVIMP_DIR)
# Add DLL dir for ctypes to find MvCameraControl.dll
os.add_dll_directory(_DLL_DIR)

from MvCameraControl_class import (
    MvCamera, MV_CC_DEVICE_INFO_LIST, MV_CC_DEVICE_INFO,
    MV_FRAME_OUT, MV_CC_HB_DECODE_PARAM, MV_CC_PIXEL_CONVERT_PARAM_EX,
    MV_ACCESS_Exclusive, MV_TRIGGER_MODE_OFF,
    MV_GIGE_DEVICE, MV_USB_DEVICE, MV_GENTL_CAMERALINK_DEVICE,
    MV_GENTL_CXP_DEVICE, MV_GENTL_XOF_DEVICE, MV_GENTL_GIGE_DEVICE,
    get_platform_functype,
    PixelType_Gvsp_Mono8, PixelType_Gvsp_RGB8_Packed,
    PixelType_Gvsp_Undefined,
)
from PixelType_header import (
    PixelType_Gvsp_HB_Mono8, PixelType_Gvsp_HB_Mono10,
    PixelType_Gvsp_HB_RGB8_Packed, PixelType_Gvsp_HB_BGR8_Packed,
    PixelType_Gvsp_HB_BayerGR8, PixelType_Gvsp_HB_BayerRG8,
    PixelType_Gvsp_HB_BayerGB8, PixelType_Gvsp_HB_BayerBG8,
)

BASE_URL = "http://127.0.0.1:8000/api/v1"

# ── Global state for callback ─────────────────────────────────
_g_frame_queue = []        # frames waiting to be sent
_g_frame_lock = __import__('threading').Lock()
_g_running = True


# ── SDK helpers (adapted from official OpenCV sample) ──────────

def _decode_and_convert(cam, stFrame):
    """Decode HB pixel format + convert to RGB, return numpy array or None."""
    stDecodeParam = MV_CC_HB_DECODE_PARAM()
    stConvertParam = MV_CC_PIXEL_CONVERT_PARAM_EX()
    memset(byref(stConvertParam), 0, ctypes.sizeof(stConvertParam))

    # Check if HB decode needed
    is_hb = stFrame.stFrameInfo.enPixelType in (
        PixelType_Gvsp_HB_Mono8, PixelType_Gvsp_HB_Mono10,
        PixelType_Gvsp_HB_RGB8_Packed, PixelType_Gvsp_HB_BGR8_Packed,
        PixelType_Gvsp_HB_BayerGR8, PixelType_Gvsp_HB_BayerRG8,
        PixelType_Gvsp_HB_BayerGB8, PixelType_Gvsp_HB_BayerBG8,
    )

    w, h = stFrame.stFrameInfo.nWidth, stFrame.stFrameInfo.nHeight

    if is_hb:
        decode_len = w * h * 3
        decode_buf = (ctypes.c_ubyte * decode_len)()
        stDecodeParam.pSrcBuf = stFrame.pBufAddr
        stDecodeParam.nSrcLen = stFrame.stFrameInfo.nFrameLen
        stDecodeParam.pDstBuf = decode_buf
        stDecodeParam.nDstBufSize = decode_len
        ret = cam.MV_CC_HBDecode(stDecodeParam)
        if ret != 0:
            return None
        stConvertParam.pSrcData = stDecodeParam.pDstBuf
        stConvertParam.nSrcDataLen = stDecodeParam.nDstBufLen
        stConvertParam.enSrcPixelType = stDecodeParam.enDstPixelType
    else:
        stConvertParam.pSrcData = stFrame.pBufAddr
        stConvertParam.nSrcDataLen = stFrame.stFrameInfo.nFrameLen
        stConvertParam.enSrcPixelType = stFrame.stFrameInfo.enPixelType

    # Convert to RGB8
    dst_ch = 3
    dst_len = dst_ch * w * h
    dst_buf = (ctypes.c_ubyte * dst_len)()
    stConvertParam.nWidth = w
    stConvertParam.nHeight = h
    stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
    stConvertParam.pDstBuffer = dst_buf
    stConvertParam.nDstBufferSize = dst_len

    ret = cam.MV_CC_ConvertPixelTypeEx(stConvertParam)
    if ret != 0:
        return None

    return np.frombuffer(dst_buf, dtype=np.uint8, count=dst_len).reshape(h, w, 3)


# ── SDK callback ───────────────────────────────────────────────

_functype = get_platform_functype()
_FrameCallbackType = _functype(None, POINTER(MV_FRAME_OUT), c_void_p, c_bool)


def _image_callback(pstFrame, pUser, bAutoFree):
    """Called by SDK for each incoming frame.  Decode and push to queue."""
    stFrame = cast(pstFrame, POINTER(MV_FRAME_OUT)).contents
    if not stFrame:
        return

    user_obj = cast(pUser, ctypes.py_object).value
    cam = user_obj

    rgb = _decode_and_convert(cam, stFrame)
    if rgb is not None:
        with _g_frame_lock:
            _g_frame_queue.append(rgb)

    if not bAutoFree and pUser is not None:
        cam.MV_CC_FreeImageBuffer(stFrame)


_CALLBACK = _FrameCallbackType(_image_callback)


# ── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MVS SDK camera grabber")
    parser.add_argument("--fps", type=float, default=10,
                        help="Target send rate (default: 10)")
    parser.add_argument("--duration", type=float, default=0,
                        help="Run for N seconds (0 = until Ctrl+C)")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    global _g_running

    # ── Init SDK ───────────────────────────────────────────────
    MvCamera.MV_CC_Initialize()
    print(f"[INFO] SDK version: 0x{MvCamera.MV_CC_GetSDKVersion():x}")

    # ── Enum devices ───────────────────────────────────────────
    deviceList = MV_CC_DEVICE_INFO_LIST()
    tlayer = (MV_GIGE_DEVICE | MV_USB_DEVICE)
    ret = MvCamera.MV_CC_EnumDevices(tlayer, deviceList)
    if ret != 0 or deviceList.nDeviceNum == 0:
        print("[FATAL] No camera found. Check GigE connection and IP config.")
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    print(f"[INFO] Found {deviceList.nDeviceNum} device(s)")

    # Connect to first device
    mvcc_dev_info = cast(deviceList.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents
    if mvcc_dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
        name_bytes = bytes(mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName)
        print(f"[INFO] GigE device: {name_bytes.decode('ascii', errors='replace').strip('\\x00')}")

    cam = MvCamera()
    ret = cam.MV_CC_CreateHandle(mvcc_dev_info)
    if ret != 0:
        print(f"[FATAL] CreateHandle failed: 0x{ret:x}")
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
    if ret != 0:
        print(f"[FATAL] OpenDevice failed: 0x{ret:x}")
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    # GigE: set optimal packet size
    if mvcc_dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
        pkt = cam.MV_CC_GetOptimalPacketSize()
        if pkt > 0:
            cam.MV_CC_SetIntValue("GevSCPSPacketSize", pkt)

    # Disable trigger
    cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)

    # Register callback
    ret = cam.MV_CC_RegisterImageCallBackEx2(_CALLBACK, ctypes.py_object(cam), True)
    if ret != 0:
        print(f"[FATAL] RegisterImageCallBackEx2 failed: 0x{ret:x}")
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    # Start grabbing
    ret = cam.MV_CC_StartGrabbing()
    if ret != 0:
        print(f"[FATAL] StartGrabbing failed: 0x{ret:x}")
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    print(f"[INFO] Grabbing started. Sending at ~{args.fps} fps to {args.base_url}")

    # ── Send loop (separate from SDK callback) ─────────────────
    interval = 1.0 / args.fps
    start_time = time.time()
    sent_count = 0
    fail_count = 0
    last_send = 0.0

    try:
        while _g_running:
            now = time.time()

            # Duration check
            if args.duration > 0 and (now - start_time) >= args.duration:
                print(f"\n[INFO] Duration {args.duration}s reached.")
                break

            # Throttle
            if now - last_send < interval:
                time.sleep(0.01)
                continue

            # Grab latest frame from queue
            with _g_frame_lock:
                if _g_frame_queue:
                    frame = _g_frame_queue[-1]  # latest only
                    _g_frame_queue.clear()
                else:
                    frame = None

            if frame is None:
                time.sleep(0.01)
                continue

            # Encode and send
            _, jpeg = cv2.imencode(".jpg", frame)
            files = {"file": (f"cam_{sent_count:06d}.jpg", jpeg.tobytes(), "image/jpeg")}

            try:
                t0 = time.time()
                resp = requests.post(
                    f"{args.base_url}/detect/visualize",
                    files=files,
                    timeout=30,
                )
                dt = (time.time() - t0) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    sent_count += 1
                    last_send = now
                    n_det = len(data.get("detections", []))
                    risk = data.get("risk_level", "-")
                    print(f"  [{sent_count:04d}] {n_det} detections | risk={risk} | {dt:.0f}ms")
                else:
                    fail_count += 1
                    print(f"  [FAIL] HTTP {resp.status_code} | {resp.text[:80]}")
            except Exception as e:
                fail_count += 1
                print(f"  [ERR] {e}")

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")

    finally:
        _g_running = False
        cam.MV_CC_StopGrabbing()
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()

        elapsed = time.time() - start_time
        print(f"\n[DONE] Sent={sent_count} Failed={fail_count} in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 无相机冒烟测试**

```bash
A:/Anaconda_envs/envs/ican/python.exe -c "import sys; sys.path.insert(0, 'Development/Samples/Python/MvImport'); from MvCameraControl_class import *; print('SDK import OK')"
```

Expected: `SDK import OK`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/camera_grabber.py
git commit -m "feat: add camera_grabber.py — MVS SDK live frame capture"
```

---

### Task 9: Docker 基础配置 (后续)

> 此任务留待 Phase 4 后执行。当前优先跑通 Windows 本机全流程。

- Create: `Dockerfile` — backend + nginx + Vue3 dist 静态文件
- Create: `docker-compose.yml` — backend 容器 + nginx 端口映射
- Create: `scripts/docker-entrypoint.sh` — 启动 uvicorn + nginx

暂不展开步骤，待 Task 1-8 全部验证通过后再细化。

---

## 执行顺序

```
Task 1: video_grabber.py         ← 立刻可做，无依赖
Task 2: stream_state.py          ← 无依赖
Task 3: schemas                  ← 无依赖，与 Task 2 并行
Task 4: backend new endpoints    ← 依赖 Task 2 + 3
Task 5: frontend API functions   ← 依赖 Task 3
Task 6: DetectPage live mode     ← 依赖 Task 4 + 5
Task 7: end-to-end test          ← 依赖 Task 1-6
Task 8: camera_grabber.py        ← 需相机硬件
Task 9: Docker                   ← 后续
```

Task 2 和 Task 3 可以并行。Task 5 可以和 Task 4 并行。
