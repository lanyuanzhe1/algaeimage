# Spec: 样机演示实时监测双栏展示 + 一键启动

**日期**: 2026-06-12
**分支**: `HSV`
**状态**: 已批准

---

## 目标

在 V2 检测页面新增实时监测功能：一键启动相机采集，左侧显示原始采集图，右侧显示 YOLO 标注结果图，固定间隔刷新。历史记录页面自动轮询新记录。

---

## 1. 架构概览

```
海康 SDK callback → frame queue (thread-safe)
    → worker thread: save raw PNG, call pipeline.run(), save result PNG
    → stream_state.add_result() with image URLs (keep last 50 in static/live/)
    → GET /detect/latest (2s polling) → LiveMonitor.vue <img src>
```

### 关键变更

- **相机 SDK 集成进 backend 进程**（不再需要独立 `camera_grabber.py`）
- **图片用 URL 引用**（非 base64 内嵌 JSON），存 `static/live/`
- **独立路由** `/detect/live`，不影响现有 `/detect` 手动上传页
- **导航栏** 移除 `el-switch` 开关，改为菜单项 "实时监测"

---

## 2. 后端

### 2.1 新增相机模块 `backend/app/services/camera.py`

从 `camera_grabber.py` 提取 SDK 逻辑，封装为类：

```
class CameraController:
    __init__()         → SDK init, enum devices, create handle, register callback
    start()            → OpenDevice + StartGrabbing + spawn worker thread
    stop()             → StopGrabbing + CloseDevice + join worker
    _callback(frame)   → decode → push to _frame_queue
    _worker()          → pop frame → save raw PNG → pipeline.run()
                       → save result PNG → stream_state.add_result()
    is_active()        → bool
```

- SDK 回调线程独立（由 MVS SDK 内部管理）
- Worker 线程消费帧队列，节流至实际管线速度（不等间隔，处理完一帧立即取下一帧最新帧）
- import SDK 之前设 `os.environ["PATH"]` + `os.add_dll_directory`

### 2.2 新增 API 端点

**`POST /api/v1/detect/stream/start`**
- 调用 `camera_controller.start()`
- 返回 `{status: "started"}` 或 `{status: "error", detail: "..."}`
- 错误场景：相机未连接、被 MVS 占用（`0x80000203`）、SDK 未初始化

**`POST /api/v1/detect/stream/stop`**
- 调用 `camera_controller.stop()`
- 返回 `{status: "stopped"}`

**修改 `GET /api/v1/detect/latest?n=10`**
- `LatestResult` schema 新增两个字段：
  - `raw_image_url: Optional[str]` — 原始采集图（`/static/live/raw_<id>.png`）
  - `result_image_url: Optional[str]` — YOLO 标注图（`/static/live/result_<id>.png`）
- 手动上传的检测结果这两个字段为 null，向后兼容

### 2.3 stream_state 增强

`add_result()` 额外保存：
- `raw_image_url: str`
- `result_image_url: str`

### 2.4 图片磁盘管理

- 目录：`code/algae_image_v2/static/live/`
- 文件命名：`raw_{frame_id}.png` / `result_{frame_id}.png`
- 缓存上限：50 帧（100 个文件）
- 自动清理：每次保存后检查，超过上限删最旧的（按文件修改时间）
- `POST /detect/stream/start` 时清空 `static/live/` 旧文件
- FastAPI `StaticFiles` 挂载 `/static` 已存在，无需额外配置

### 2.5 Backend 启动流程变更

```python
# backend/app/main.py lifespan
async def lifespan(app):
    # ... existing model loading ...
    
    # Init camera (lazy — don't open device yet)
    try:
        from .services.camera import camera_controller
        app.state.camera_controller = camera_controller
    except Exception as e:
        logger.warning(f"Camera SDK not available: {e}")
        app.state.camera_controller = None
    
    yield
    # shutdown: stop camera if running, finalize SDK
```

---

## 3. 前端

### 3.1 新页面 `views/LiveMonitor.vue`

**布局**:
```
┌─────────────────────────────────────────┐
│  [▶ 开始采集]  [⏹ 停止]    ● 采集中  │
│                             12帧 1.2fps │
├─────────────────────────────────────────┤
│  原始采集图          YOLO 检测结果       │
│  (RGB 原图)          (带框+标签+风险色) │
│                                         │
│  640×512             640×512            │
├─────────────────────────────────────────┤
│  StatsCards (5 cards)                   │
├─────────────────────────────────────────┤
│  ResultTable                            │
└─────────────────────────────────────────┘
```

**状态机**:

| 状态 | 按钮 | 双栏 | 轮询 |
|------|------|------|------|
| idle | 开始可点，停止灰色 | 占位图 "等待采集开始" | 无 |
| starting | 开始 loading，停止灰色 | 占位图 | 无 |
| running | 开始灰色，停止可点 | 实时图像 | 2s 轮询 |
| stopping | 开始灰色，停止 loading | 最后一帧 | 停止 |
| error | 开始可点，停止灰色 | 错误提示 | 无 |

**数据流**:
```
点击开始 → POST /detect/stream/start
  → 成功 → setInterval(2s) → GET /detect/latest + GET /detect/stream-status
  → 失败 → 显示错误

轮询回调:
  latest.results[0].raw_image_url  → 左图 <img :src>
  latest.results[0].result_image_url → 右图 <img :src>
  streamStatus.active === false → 自动切到 error/idle

点击停止 → POST /detect/stream/stop → clearInterval
```

**图片加载优化**: `<img>` 添加 `key` 绑定 URL，浏览器自动缓存同一 URL，新帧 URL 变化时自动刷新。

### 3.2 导航栏变更 (`App.vue`)

**删除**:
- `el-switch` + `live-toggle` 整个区块（第 28-38 行）
- `@change="store.toggleLiveMode"` 双重触发 bug 随代码删除消失

**新增**:
- `el-menu-item index="/detect/live"` — "实时监测"
- `el-menu-item index="/detect"` text 改为 "手动检测"（原名 "检测工具"）

### 3.3 路由注册

```javascript
// router/index.js
{ path: '/detect/live', name: 'LiveMonitor', component: () => import('@/views/LiveMonitor.vue') }
```

### 3.4 历史页自动刷新 (`HistoryPage.vue`)

- `onMounted` 启动 `setInterval(3s)` 轮询 `GET /history?page=1&limit=20`
- 对比最新记录的 `id`：如有新记录，`unshift` 到列表顶部
- `onUnmounted` 清除定时器
- 分页切换时暂停自动刷新，回到第 1 页后恢复

### 3.5 Pinia Store 重构 (`stores/detect.js`)

**删除**:
- `liveMode`, `toggleLiveMode` — 不再需要全局开关

**保留**:
- `liveResults`, `streamStatus`, `startPolling`, `stopPolling` — 功能不变

**新增**:
- `startStream()` — `POST /detect/stream/start`
- `stopStream()` — `POST /detect/stream/stop`
- `isStreaming` ref — 当前采集状态

**Cleanup**: `startPolling/stopPolling` 改为 `startStreamPolling/stopStreamPolling`，语义更明确。

### 3.6 API 层新增 (`api/index.js`)

```javascript
export function startStream() { return api.post('/detect/stream/start') }
export function stopStream() { return api.post('/detect/stream/stop') }
```

---

## 4. 参数汇总

| 参数 | 值 | 说明 |
|------|-----|------|
| 前端轮询间隔 | 2s | 匹配管线处理速度 |
| 历史页轮询间隔 | 3s | 历史记录变化慢，降低后端负载 |
| 图片磁盘缓存 | 50 帧 | 用户指定 |
| 内存 stream_state | 200 条 | 保持现有 |
| 图像格式 | PNG | 无损，适合显微图像 |

---

## 5. 错误处理

| 场景 | 后端行为 | 前端展示 |
|------|----------|----------|
| SDK DLL 缺失/import 失败 | lifespan warning, `camera_controller = None` | N/A（启动即知） |
| Start 时相机未连接 | 返回 `{status: "error", detail}` | el-alert 错误提示 |
| Start 时相机被 MVS 占用 | `OpenDevice` 返回 `0x80000203` | "相机被占用，请关闭 MVS 客户端" |
| 采集过程中相机断开 | `is_active()` 返回 false | 轮询检测 `active=false` → 自动停采，显示警告 |
| 管线处理异常 | catch 异常，打印日志，跳过该帧 | 无影响，下一帧继续 |

---

## 6. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/camera.py` | **新建** | 相机控制模块 |
| `backend/app/services/stream_state.py` | 修改 | add_result 加 image_url 字段 |
| `backend/app/routes.py` | 修改 | 新增 start/stop 端点，修改 /detect/latest |
| `backend/app/main.py` | 修改 | lifespan 初始化 camera_controller |
| `shared/schemas.py` | 修改 | LatestResult 加 raw/result image_url |
| `frontend/src/views/LiveMonitor.vue` | **新建** | 实时监测页面 |
| `frontend/src/views/HistoryPage.vue` | 修改 | 自动轮询 |
| `frontend/src/App.vue` | 修改 | 删除 switch，加菜单项 |
| `frontend/src/router/index.js` | 修改 | 注册 /detect/live |
| `frontend/src/stores/detect.js` | 修改 | 重构 live 逻辑 |
| `frontend/src/api/index.js` | 修改 | 新增 startStream/stopStream |

---

## 7. 不变更

- `camera_grabber.py` — 保留不动（调试/独立测试仍可用）
- `video_grabber.py` — 保留不动
- `/detect` 手动检测页 — 不改
- `/detect/visualize` 端点 — 不改
- Dashboard、设备管理、人工复核页 — 不改
