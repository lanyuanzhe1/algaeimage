---
name: demo-workflow-architecture
description: 样机演示流程架构 — SDK直连相机、stream_state缓冲、前端2s轮询、已知坑点
metadata:
  type: project
---

## 样机演示架构

相机 SDK (camera_grabber.py) → POST /detect/visualize → core_engine 管线 → stream_state 缓冲 → GET /detect/latest (前端 2s 轮询)

### 三组件

- `camera_grabber.py`: SDK ctypes 回调→numpy→JPEG POST, 5fps 节流。DLL 在 `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64`，import 前须设 PATH
- `video_grabber.py`: cv2 读 AVI 回放，无相机时用
- `stream_state.py`: `threading.Lock` 保护，`add_result()` 在 POST 返回前调用，`get_latest()`/`get_status()` 供轮询

### 已知 bug

- **实时监测不刷新**: `v-model` + `@change="toggleLiveMode"` 双重触发，开关来回翻。修复: `watch(liveMode)` 替代 `@change`
- **MVS 冲突**: SDK 需独占相机，MVS 客户端必须关闭（错误码 `0x80000203`）

### 关键路径

- MVS: `A:\Program Files\MVS`
- DLL: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64`
- Node: `A:\Program Files\nodejs` (npm 构建须通过 Python subprocess)
