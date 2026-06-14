---
name: demo-workflow-architecture
description: 样机演示流程架构 — 2026-06-13 全链路贯通，含性能优化与时间戳修复
metadata:
  type: project
---

## 样机演示架构（当前状态）

```
SDK callback → frame queue (threading.Lock)
    → worker thread: pipeline.run_ndarray(frame)  # 无磁盘 I/O
    → save raw.jpg + result.jpg (JPEG quality 90)
    → stream_state.add_result() with image URLs
    → batch DB insert (every 10 frames, executemany)
    → GET /detect/latest (2s polling) → LiveMonitor.vue <img src>
```

### 五组件

- `backend/app/services/camera.py`: CameraController 类，SDK ctypes 回调→numpy→worker 线程。import 前须设 PATH
- `backend/app/services/video.py`: VideoController 类，cv2 逐帧读取 AVI/MP4 模拟相机输入，无硬件相机时可用
- `backend/app/services/stream_state.py`: `threading.Lock` 保护，`add_result()` 存 id/filename/image_urls，`get_latest()`/`get_status()` 供轮询
- `backend/app/services/pipeline.py`: PipelineRunner，管线 `结构张量偏振 → RDN(62.46dB) → I_enh v2(α=0.6) → YOLOv8s`，`PIPELINE_MAX_WIDTH=1024` 速度控制
- `frontend/src/views/LiveMonitor.vue`: el-tabs 双模式（相机采集|视频演示），状态 derived from Pinia store（2026-06-14 修复停止按钮+切Tab状态丢失）

### 后端端点

| 路由 | 说明 |
|------|------|
| `POST /api/v1/detect/stream/start` | 启动相机采集 + spawn worker 线程 |
| `POST /api/v1/detect/stream/stop` | 停止采集 + 清理资源 |
| `GET /api/v1/detect/latest?n=10` | 最近 N 条（含 raw_image_url + result_image_url） |
| `GET /api/v1/detect/stream-status` | 采集状态（active/total_frames/effective_fps） |
| `POST /api/v1/detect/stream/start-video` | 视频文件作为检测源 |
| `POST /api/v1/detect/stream/stop-video` | 停止视频流 |
| `GET /api/v1/detect/video-list` | 扫描 video/ 目录返回可用 mp4 |
| `GET /api/v1/detect/video-status` | 视频流状态 |

### 速度剖析（2026-06-14）

**RDN 瓶颈**（结构张量+RDN 管线，GPU RTX 4050）：

| 分辨率 | 偏振 | RDN | I_enh | YOLO | 总耗时 | fps |
|--------|------|-----|-------|------|--------|-----|
| 2080×1540 | 0.9s | 320s | 0.5s | 1.1s | 322s | 0.003 |
| 1024×758 | 0.2s | 2.3s | 0.07s | 0.1s | 2.7s | 0.37 |
| 640×474 | 0.08s | 0.6s | 0.03s | 0.2s | 0.9s | 1.1 |

瓶颈 100% 在 RDN（DenseLayer concat 通道膨胀 16→112）。`PIPELINE_MAX_WIDTH=1024` 作为默认值。

**旧优化（HSV 无 RDN 时代）**:
- `pipeline.run_ndarray(frame)`: 跳过 temp 文件 I/O
- JPEG quality 90 替代 PNG
- 批量 DB 写入（每 10 帧 `executemany`）

### 时间戳修复

- 根因: 实际表用 `CURRENT_TIMESTAMP`（UTC），非 database.py 定义的 `localtime`
- 修复: camera worker 显式设 `time.localtime()`，DB default 改 `datetime('now','+8 hours')`

### 已知 bug 修复

- ~~**实时监测不刷新**~~: `v-model` + `@change` 双重触发
- ~~**切页停止采集**~~: Store start()/stop() 管理轮询
- ~~**切 Tab 状态丢失**~~ (2026-06-14): 组件本地 `state` ref 与 Pinia store `isStreaming` 断开同步。修复: `onMounted` 检查 `store.isStreaming` 恢复状态，`store.stop()` try/catch 保证状态重置
- ~~**停止按钮无效**~~ (2026-06-14): API 调用失败时 `isStreaming`/`streamMode` 不重置。修复: try/catch 包裹 API，状态重置 always executes
- frontend vitest 测试覆盖: `detect-store.test.js` (stop lifecycle + interval clear + cross-remount)
- ~~**历史页不更新**~~
- ~~**时间戳 UTC+0**~~

### 关键路径

- MVS: `A:\Program Files\MVS`
- DLL: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64`
- Node: `A:\Program Files\nodejs`（前端构建须用 cmd.exe 方式）
- Live images: `static/live/`（JPEG, 50 帧缓存）
- DB: `backend/data/history.db`
