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

### 三组件

- `backend/app/services/camera.py`: CameraController 类，SDK ctypes 回调→numpy→worker 线程。import 前须设 PATH
- `backend/app/services/stream_state.py`: `threading.Lock` 保护，`add_result()` 存 id/filename/image_urls，`get_latest()`/`get_status()` 供轮询
- `frontend/src/views/LiveMonitor.vue`: 状态机（idle/starting/running/stopping/error），双栏展示，onMounted 检测相机状态自动恢复

### 后端端点

| 路由 | 说明 |
|------|------|
| `POST /api/v1/detect/stream/start` | 启动相机采集 + spawn worker 线程 |
| `POST /api/v1/detect/stream/stop` | 停止采集 + 清理资源 |
| `GET /api/v1/detect/latest?n=10` | 最近 N 条（含 raw_image_url + result_image_url） |
| `GET /api/v1/detect/stream-status` | 采集状态（active/total_frames/effective_fps） |

### 性能优化（2026-06-13）

- `pipeline.run_ndarray(frame)`: 跳过 temp 文件 I/O（省 ~200ms/帧）
- JPEG quality 90 替代 PNG: 编码快 5-10x，文件小 10-20x（省 ~100ms/帧）
- 批量 DB 写入（每 10 帧 `executemany`）: 省 sqlite3 connect/commit 开销
- 预期有效 FPS: 1.5-1.8（原 0.86）

### 时间戳修复

- 根因: 实际表用 `CURRENT_TIMESTAMP`（UTC），非 database.py 定义的 `localtime`
- 修复: camera worker 显式设 `time.localtime()`，DB default 改 `datetime('now','+8 hours')`

### 已知 bug 修复

- ~~**实时监测不刷新**~~: `v-model` + `@change="toggleLiveMode"` 双重触发。修复: 删除 el-switch，改独立路由 /detect/live + Store 管理轮询
- ~~**切页停止采集**~~: LiveMonitor onUnmounted 停轮询。修复: Store start()/stop() 自动管理轮询，onMounted 恢复状态
- ~~**历史页不更新**~~: camera worker 只写 stream_state。修复: worker 批量写 history.db
- ~~**时间戳 UTC+0**~~: CURRENT_TIMESTAMP。修复: 显式 +8 hours

### 关键路径

- MVS: `A:\Program Files\MVS`
- DLL: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64`
- Node: `A:\Program Files\nodejs`（前端构建须用 cmd.exe 方式）
- Live images: `static/live/`（JPEG, 50 帧缓存）
- DB: `backend/data/history.db`
