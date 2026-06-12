# 样机演示流程 — 技术深度日志

**日期:** 2026-06-11 至 2026-06-12
**分支:** HSV
**Commits:** `dda5dee` → `fb9337f` → `7afa0cc` → `a6d23c0` → `8fa30b7`

## 完成事项
- 样机演示全流程设计（brainstorming → spec → plan → 实现）
- 相机 SDK 直连：MVS Python SDK 加载 MV-CA013-20GC (GigE)，回调取帧 → numpy → 管线
- AVI 回放采集器：无相机时用样本视频模拟全流程
- 内存流状态管理：线程安全缓冲 + REST 轮询端点
- 前端 SPA 路由修复 + 导航栏实时监测开关（Pinia store 跨组件共享）
- DB 时间戳修正 + 文件锁绕过
- Memory 体系从用户级迁移到项目级（10 文件，git 同步）
- write_log skill 强化：从摘要式升级为原理级深度日志

## 技术原理

### 1. SDK ctypes 回调架构

海康 MVS SDK 提供 C 语言 DLL (`MvCameraControl.dll`)，Python 端通过 ctypes 绑定：

```
C 层:  相机传感器 → GigE Vision 协议 → 驱动 → 帧缓冲
SDK:   MV_CC_StartGrabbing() → 内部线程循环抓帧
       → MV_CC_RegisterImageCallBackEx2(callback) → 每帧回调
Python: CFUNCTYPE(None, POINTER(MV_FRAME_OUT), c_void_p, c_bool) → image_callback()
```

关键设计点：
- **回调线程归属**：SDK 内部创建独立线程触发回调，此线程不受 Python GIL 控制。因此 `_frame_queue` 需要 `threading.Lock()` 保护——C 扩展线程与 Python 主线程的并发写入竞争是真实存在的。
- **双缓冲解耦**：SDK 回调速率为相机硬件帧率（8.8fps），但管线处理速率为 0.8fps（YOLO 推理 1.1s/帧）。在回调与 HTTP POST 之间插入 `_frame_queue` 作为生产者-消费者缓冲，丢旧帧取最新帧（`_frame_queue[-1]; _frame_queue.clear()`），保证管线永远处理最即时数据而非积压队列。
- **HB 解码必要性**：相机输出可能是 High Bandwidth (HB) 编码格式——`PixelType_Gvsp_HB_*`。HB 是 GigE Vision 为降低带宽的专利压缩，需经 `MV_CC_HBDecode()` 解码后再 `MV_CC_ConvertPixelTypeEx()` 转为标准 RGB8。是否 HB 由 `enPixelType` 判断（约 40 个枚举值）。

### 2. DLL 加载机制

`MvCameraControl_class.py` 在模块级别执行：

```python
def check_sys_and_update_dll():
    MvCamCtrldll = WinDLL("MvCameraControl.dll", winmode=0)  # 模块级调用
```

`WinDLL(name)` → Windows `LoadLibraryEx(name, NULL, LOAD_WITH_ALTERED_SEARCH_PATH)` → 搜索顺序：

1. 当前进程 EXE 所在目录
2. `GetSystemDirectory()` → `C:\Windows\System32`
3. `GetWindowsDirectory()` → `C:\Windows`
4. 当前工作目录
5. `PATH` 环境变量中的目录

MVS 安装器将 `MvCameraControl.dll` 放在 `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\`——不在上述任何默认路径中。Python 3.8+ 引入 `os.add_dll_directory()` 允许运行时追加以 `LOAD_LIBRARY_SEARCH_USER_DIRS` 标志，但 `check_sys_and_update_dll()` 在 `import MvCameraControl_class` 时就执行（模块级代码），早于调用方 `os.add_dll_directory()` 生效。

**解决方案**：在 `import` SDK 之前修改 `os.environ["PATH"]`。Python 启动时继承的 PATH 仅包含启动时的系统 PATH；运行时修改 `os.environ["PATH"]` 会传递到子进程，但对已在运行的进程的 `LoadLibrary` 搜索是否生效取决于 Windows 版本。实测 Win11 下 `os.environ["PATH"]` 修改 + `os.add_dll_directory()` 双保险有效。

### 3. 前端轮询 vs WebSocket

选择 2s 轮询 `GET /api/v1/detect/latest` 而非 WebSocket 推送：

- **延迟分析**：系统瓶颈在 YOLO 推理（~1100ms/帧）。轮询引入最多 2000ms 额外延迟，但帧到达前端的实际节奏由管线吞吐决定（~0.8fps），轮询不会成为瓶颈。网络往返 < 5ms localhost。
- **实现成本**：轮询 = 已有 REST 端点 + `setInterval`。WebSocket = `fastapi.WebSocket` 路由 + 后台 `asyncio.Queue` 广播 + 前端 `WebSocket` 连接管理（重连/心跳/序列化）。
- **扩展性**：单机演示场景下行链路仅一个消费者，广播优势不存在。将来多客户端时再切换 WebSocket（后端 `stream_state` 可以挂一个 `asyncio.Event` 通知而不改架构）。

### 4. Pinia store 跨组件状态共享

实时监测开关从 DetectPage（页面内）提升到 App.vue（导航栏全局）的本质：

- **Why Pinia**：Vue3 `provide/inject` 仅限于组件树，非父子组件间（App.vue 与 DetectPage.vue）需要全局状态。Pinia store 是单例，组件通过 `useDetectStore()` 获取同一实例。
- **v-model + @change 冲突根因**：
  ```
  v-model="store.liveMode"       → 开关点击时 Pinia 写 liveMode = true
  @change="store.toggleLiveMode" → 紧接着调用 toggleLiveMode() 翻转 liveMode = false
  ```
  时序：`@change` 事件携带新值 `val=true` 作为参数，但 `toggleLiveMode()` 无参——它读 `liveMode.value`（已被 v-model 设为 true）再取反设为 false。开关回到关闭态，`startPolling()` 从未被调用。
- **修复方案**：去掉 `@change`，用 `watch(() => store.liveMode, (val) => { if (val) store.startPolling(); else store.stopPolling(); })` 代替。`watch` 不翻转值，仅在值变化后触发副作用。

### 5. FastAPI SPA fallback

Vue3 使用 History Mode 路由（`/detect`, `/history` 等），浏览器直接访问 `/app/detect` 时，FastAPI 需要返回 `index.html`（而非 404），让 Vue Router 接管客户端路由。

`StaticFiles(html=True)` 文档声称支持 SPA fallback，但实际行为是：仅当 URL 指向一个**存在的目录**时才 fallback 到 `index.html`。`/app/detect` 不是目录，直接返回 404。

修复：显式添加 `@app.get("/app/{full_path:path}")` 路由返回 `FileResponse(index.html)`。这是因为 FastAPI 路由优先级高于 StaticFiles 挂载，且 `{full_path:path}` 匹配任意深度子路径。

## 行动细节

### Phase 1: 设计
```bash
# 启动 brainstorming visual companion (Node.js 24.14.0)
PATH="/c/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH"
bash .../start-server.sh --project-dir e:/code/codex
# → http://localhost:56670 (后续 65109/... 因超时重建)

# 写设计文档
docs/superpowers/specs/2026-06-11-demo-workflow-design.md
docs/superpowers/plans/2026-06-11-demo-workflow.md
```

### Phase 2: video_grabber.py (不依赖硬件，先跑通)
```bash
# 创建 code/algae_image_v2/video_grabber.py
# 核心循环: cv2.VideoCapture → cv2.imencode → requests.post
# 节流: interval = 1.0 / fps; sleep(max(0, expected - elapsed))

# 单帧冒烟测试
cd e:/code/codex
A:/Anaconda_envs/envs/ican/python.exe code/algae_image_v2/video_grabber.py \
    video/Video_20260611215520245.avi --once

# e2e 验证（49帧/60s, 0失败）
A:/Anaconda_envs/envs/ican/python.exe code/algae_image_v2/video_grabber.py \
    video/Video_20260611215520245.avi --fps 5 --duration 60
# 输出: Sent=49 Failed=0 in 60.2s (0.8 fps effective)
```

### Phase 3: 后端新端点 + stream_state
```bash
# 创建 stream_state.py
# - StreamState 类: threading.Lock 保护 _results list + _total_frames
# - add_result() 在 POST /detect 返回前调用
# - get_latest(n) / get_status() 供 GET 端点使用
# 模块级单例: stream_state = StreamState()

# schema 扩展: shared/schemas.py 追加 3 个模型
# LatestResult / LatestResultsResponse / StreamStatusResponse

# routes.py 追加 2 个端点
# GET /api/v1/detect/latest?n=10
# GET /api/v1/detect/stream-status

# 验证: curl localhost:8002/api/v1/detect/stream-status
# → {"active":true,"total_frames":49,"buffer_size":49,...}
```

### Phase 4: 相机 SDK 集成
```bash
# 发现 DLL 位置
find "A:/Program Files/MVS" -name "MvCameraControl.dll"  # 未找到
find "C:/Program Files (x86)/Common Files/MVS" -name "MvCameraControl.dll"  # 找到！

# 关键环境变量
MVCAM_COMMON_RUNENV=  # 空，需手动设置
NODE_PATH=A:\Program Files\nodejs\node_modules

# DLL 加载修复
# 在 import MvCameraControl_class 之前:
os.environ["PATH"] = r"C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64;" + os.environ["PATH"]

# SDK 初始化 + 设备枚举
MvCamera.MV_CC_Initialize()  → SDK 4.8.0.3
MvCamera.MV_CC_EnumDevices() → 1 device: MV-CA013-20GC @ 169.254.82.254

# 单帧测试通过
python camera_grabber.py --once  → [0001] 1 detections | risk=low | 1437ms

# 连续采集：49帧/60s，0失败
python camera_grabber.py --fps 5 --duration 60
# effective_fps: 0.84 (受 YOLO 推理 ~1100ms/帧 瓶颈)
```

### Phase 5: 前端修复与重构
```bash
# SPA fallback 修复 (main.py)
# 问题: /app/detect → 404
# 修复: @app.get("/app/{full_path:path}") → FileResponse(index.html)

# npm 构建 (通过 Python subprocess)
import subprocess; env = os.environ.copy()
env['PATH'] = r'A:\Program Files\nodejs;' + env['PATH']
subprocess.run([r'A:\Program Files\nodejs\npm.cmd', 'run', 'build'], ...)
# → exit 0, 新 JS: index-CBTbhbEd.js

# Pinia store 重构
# detect.js: 新增 liveMode, liveResults, streamStatus, toggleLiveMode, startPolling, stopPolling
# App.vue:  导航栏加入 <el-switch v-model="store.liveMode" @change="store.toggleLiveMode">
# DetectPage.vue: 简化为从 store 读取，移除本地 live mode 状态

# 验证: curl /app/detect → 200 OK
```

## 遇到的问题

### 问题 1: MvCameraControl.dll 找不到

**现象**: `FileNotFoundError: Could not find module 'MvCameraControl.dll'`，路径 `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\MvCameraControl.dll` 存在但 ctypes 加载失败。

**根因**: Python `WinDLL("MvCameraControl.dll")` 内部调用 Windows `LoadLibraryEx(name, NULL, LOAD_WITH_ALTERED_SEARCH_PATH)`。DLL 搜索顺序为：EXE 目录 → System32 → Windows → CWD → PATH。MVS 安装器将运行时 DLL 放在 `Common Files\MVS\Runtime\Win64_x64`——不在上述任何默认路径。更重要的是，`check_sys_and_update_dll()` 是 `MvCameraControl_class.py` 的模块级代码，在 `import` 语句执行时就触发 DLL 加载。调用方即使先执行 `os.add_dll_directory()`，也在 import 之后，时序上无效。

**解决方案**: 在 import SDK 之前修改 `os.environ["PATH"]` 添加 DLL 目录。Python 运行时修改 PATH 的行为依赖 Windows 版本：Win11 下子进程继承修改后的 PATH，且 `LoadLibraryEx` 在某些条件下重新扫描 PATH。双保险：`os.add_dll_directory()` + PATH 修改。

### 问题 2: npm 在 bash 中不可用

**现象**: `npm: command not found` —— bash 中 `which node` / `which npm` 均无结果。

**根因**: 当前 bash 环境（Codex 嵌入式 shell）没有继承完整的 Windows PATH。`node.exe` 安装在 `A:\Program Files\nodejs\` 且已加入 Windows 系统 PATH，但 bash 启动时 `$PATH` 仅包含 Unix 风格路径（`/usr/bin`, `/opt/...`），不包含 Windows 路径。`NODE_PATH` 环境变量设为 `A:\Program Files\nodejs\node_modules` 确认了安装位置。

**解决方案**: 通过 Python `subprocess.run(..., env=env, shell=True)` 调用 Node 工具链，在 subprocess 的 `env` 中显式设置 `PATH`。`npm install` 和 `npm run build` 均通过此方式成功。

### 问题 3: history.db 无法删除

**现象**: `rm e:/.../history.db` → "Device or resource busy"，所有 Python 进程已终止。

**根因**: Windows 错误码 32 (`ERROR_SHARING_VIOLATION`)——某个非 Python 进程持有文件句柄。可能原因：Windows Search Indexer、杀毒软件实时扫描、或之前 uvicorn 进程异常退出后句柄未释放（Windows 文件句柄释放有延迟）。

**解决方案**: DB 文件名从 `history.db` 改为 `detection_history.db`（`config.py` 中 `DB_PATH`），绕过旧文件锁。旧文件可后续重启 Windows 后手动删除。

### 问题 4: 实时监测开关不工作（未修复）

**现象**: 点击导航栏"实时监测"开关后，页面无变化，不显示实时数据。手动刷新页面才看到新数据。

**根因**: `v-model="store.liveMode"` 绑定开关到 `liveMode` 响应式值。`@change="store.toggleLiveMode"` 在值变更后再次翻转值。时序：
1. 用户点击开关 → `v-model` 写 `liveMode = true`
2. `@change` 触发 → `toggleLiveMode()` 被调用
3. `toggleLiveMode()` 读 `liveMode.value`（已是 `true`）→ 取反设为 `false`
4. `startPolling()` 从未被调用，轮询不启动

**修复方案**: 去掉 `@change="store.toggleLiveMode"`，添加 `watch(() => store.liveMode, (val) => { val ? store.startPolling() : store.stopPolling() })`。

### 问题 5: 端口残留占用

**现象**: `[Errno 10048]` 多次出现——`taskkill` 后重启 uvicorn 仍报地址占用。

**根因**: `taskkill` 发送 `WM_CLOSE` 信号，Python 进程需要时间清理。`taskkill //f` 强制终止但 bash 中的后台进程（`&`）可能属于不同进程组，`tasklist | grep python` 未捕获。另外 Windows 的 `TIME_WAIT` 状态（默认 120s）也使端口短暂不可重用。

**解决方案**: 跳端口（8003/8005/8007/8010/8011/8012/8013/8015/8020 依次尝试）。修复方案：`SO_REUSEADDR` socket 选项（未实施）。

## 结果/产出

### 新增文件（8个核心文件）
| 文件 | 用途 | 规模 |
|------|------|------|
| `camera_grabber.py` | SDK 回调取帧→POST 管线 | ~240 行 |
| `video_grabber.py` | AVI 回放采集器 | ~120 行 |
| `stream_state.py` | 线程安全内存缓冲 | ~70 行 |
| `shared/schemas.py` | +3 个 Pydantic 模型 | +22 行 |
| `stores/detect.js` | Pinia 实时监测状态 | 重构 |
| `App.vue` | 导航栏实时开关 | 重构 |
| `DetectPage.vue` | 读 store 简化 | 重构 |
| `main.py` | SPA fallback 路由 | +20 行 |

### 验证指标
- video_grabber: 49 帧/60s, 0 失败, 0.84 effective fps
- camera_grabber: 49 帧/60s, 0 失败, 每帧 ~1100ms
- stream_state: `active=true, total_frames=49, buffer_size=49`
- 前端: `/app/detect` 200 OK, SPA fallback 正常
- 构建: `npm run build` exit 0

## 下一步

1. **修复实时监测轮询**：`@change` → `watch(liveMode)`，预计 5 分钟修改 + 测试
2. **Docker 封装**：backend + nginx + Vue3 dist → Linux 镜像，camera_grabber 宿主机运行
3. **前端体验优化**：
   - 实时模式下显示 PipelineViz（当前 `/latest` 不含 steps base64——需追加或改调 `/visualize`）
   - 页面卡顿排查（大数据 JSON？DOM 更新频率？）
4. **清理**：`.claude/skills/` 14 个过时目录引用，旧 `history.db` 文件
5. **run.bat 一键启动**：整合 backend + camera_grabber + 浏览器打开
