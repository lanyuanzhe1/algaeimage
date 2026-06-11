# 样机演示流程 — 开发会话

**日期:** 2026-06-11 至 2026-06-12
**分支:** HSV

## 完成事项
- Brainstorming + 设计文档完整流程（spec + plan）
- Memory 体系迁移：用户级 → 项目级 `.claude/memory/`（10 文件, git 同步）
- `video_grabber.py` — AVI 回放模式，e2e 验证通过（49 帧/60s, 0 失败）
- `camera_grabber.py` — MVS SDK 直连 MV-CA013-20GC, 5fps 节流, e2e 验证通过
- `stream_state.py` — 线程安全内存缓冲，`/detect/latest` + `/detect/stream-status` 端点
- 前端 SPA fallback 修复 — `main.py` 添加 `/app/{full_path:path}` 路由
- 前端实时监测导航栏重构 — Pinia store 共享状态，switch 移至 App.vue nav bar
- 前端构建验证通过（npm run build, exit 0）

## 技术细节

### 相机 SDK
- 型号: MV-CA013-20GC, GigE, IP 169.254.82.254
- SDK 版本: 0x4080003
- DLL 路径: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\MvCameraControl.dll`
- Python SDK: `A:\Program Files\MVS\Development\Samples\Python\MvImport`
- 关键修复: `os.environ["PATH"]` 须在 import SDK 之前加入 DLL 目录
- Node.js: `A:\Program Files\nodejs\` (NODE_PATH 环境变量)

### 架构
```
相机 SDK callback → numpy RGB → JPEG → POST /api/v1/detect/visualize
→ core_engine 管线 → stream_state.add_result()
→ GET /api/v1/detect/latest (2s 轮询) → Vue3 前端
```

### 关键提交
- `dda5dee` feat: demo workflow — camera SDK + video replay + live polling
- `fb9337f` fix: SPA fallback for Vue3 frontend
- `7afa0cc` refactor: move live monitoring toggle to nav bar
- `a6d23c0` fix: local time DB timestamps, rename db to avoid file lock

## 遇到的问题

1. **MvCameraControl.dll 找不到**: Python SDK 用 `WinDLL("MvCameraControl.dll")` 按名加载，DLL 不在 PATH。修复：`os.environ["PATH"]` 预先加入 `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64`
2. **npm 不在 bash PATH**: 通过 `NODE_PATH` 环境变量找到 `A:\Program Files\nodejs\`，用 Python subprocess 调用 npm
3. **SPA fallback 404**: FastAPI `StaticFiles(html=True)` 不处理子路径。修复：显式添加 `@app.get("/app/{full_path:path}")` 返回 index.html
4. **history.db 被系统进程锁死**: 无法删除或重命名。修复：DB 文件名改为 `detection_history.db`
5. **时间戳存 UTC**: SQLite `CURRENT_TIMESTAMP` 返回 UTC。修复：改为 `datetime('now','localtime')`
6. **实时监测不自动刷新（未修复）**: `v-model="store.liveMode"` + `@change="store.toggleLiveMode"` 双重触发，导致 liveMode 来回翻转，轮询从未启动。需用 `watch(liveMode)` 替代 `@change`

### 其他问题
- 端口 8000 被僵尸进程占用，多次切换到 8003/8005/8007/8010 等端口
- camera_grabber 与 MVS 客户端不能同时访问相机（SDK 需要独占）

## 结果/产出

### 新增文件
- `code/algae_image_v2/video_grabber.py`
- `code/algae_image_v2/camera_grabber.py`
- `code/algae_image_v2/backend/app/services/stream_state.py`
- `.claude/memory/` 10 个记忆文件
- `docs/superpowers/specs/2026-06-11-demo-workflow-design.md`
- `docs/superpowers/plans/2026-06-11-demo-workflow.md`
- `demo_workflow_design_0611.md`
- `C:\Users\HP\.claude\.mcp.json` (Playwright MCP 配置)

### 修改文件
- `backend/app/routes.py` — 2 个新端点 + stream_state 集成
- `backend/app/main.py` — SPA fallback 路由
- `backend/app/database.py` — 本地时间戳
- `backend/app/config.py` — DB 改名
- `shared/schemas.py` — 3 个新模型
- `frontend/src/App.vue` — 导航栏实时监测
- `frontend/src/stores/detect.js` — Pinia live mode
- `frontend/src/views/DetectPage.vue` — 简化，读 store
- `frontend/src/api/index.js` — 2 个新 API 函数

## 下一步
1. 修复实时监测：`@change` → `watch(liveMode)`
2. 测试前端自动刷新
3. Docker 封装
4. 清理 `.claude/skills/` 过时目录引用
