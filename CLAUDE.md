# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概览

本仓库包含藻类显微图像偏振检测的完整研究到产品管线：

| 目录 | 定位 |
|------|------|
| `code/algae_image_v1/` | **V1.0 产品** — 桌面工具，单机运行，95类 LifeWatch |
| `code/algae_image_v2/` | **V2.0 产品（当前主线）** — 5类 FMPD，HSV 偏振，已封装 exe |
| `code/algae_guardian/` | 研究型项目 — 训练、评估、完整实验 |
| `code/Polar_sim_0520/` | 结构张量管线实验 (mAP50 82.24%)，V1 产品的算法来源 |
| `code/Polar_sim_0522/` | HSV 偏振实验 (mAP50 37.9%，已废弃)，含 Docker 训练环境 |
| `code/RDN_HSV_0526/` | HSV+RDN 对照实验 — 证明 HSV 不需要 RDN，V2 跳过 RDN 的实验依据 |
| `code/SPDRDN/` | RDN 网络原始研究 (独立 git 仓库)，含 MATLAB 评估脚本 |

`docs/` 目录包含 13 份参考文档 (训练总结、交接文档、数据集调查等)。

`@code/README.md` — 完整目录地图（含状态标记）和模型权重清单
`@docs/handoff-20260524-algae-guardian-v1.md` — V1 构建交接文档
`@docs/v1_product_build_0524.md` — V1 产品构建日志

**当前分支**: `HSV`。

---

## 一、algae_image_v1 — V1.0 产品

### 启动

```bash
cd e:/code/algaeimage/code/algae_image_v1
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# 或双击 run.bat
```

访问: `http://localhost:8000/docs` (API), `http://localhost:8000/app/` (前端)

### 处理管线 (不可变更顺序，V1专用)

```
RGB原图 → 结构张量偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh v2去散射增强 → YOLOv8s检测(95类LifeWatch)
```

### 架构

```
frontend/ (原生HTML/CSS/JS, 无构建工具, Chart.js CDN)
    ↓ HTTP REST
backend/ (FastAPI 薄层: 路由 + 参数校验 + SQLite持久化)
    ↓ import
core_engine/ (纯Python库, 零框架依赖: numpy/PyTorch/cv2)
```

**设计原则**: core_engine 不 import FastAPI/数据库，可直接被 PyInstaller 或 C++ 调用。backend 只做编排，业务逻辑全在 core_engine。

**backend 实现要点**:
- `main.py` 使用 `lifespan` async context manager (非已弃用的 `on_event`)
- `services/pipeline.py` — `PipelineRunner` 类编排全部 5 阶段管线
- `config.py` — 集中管理路径、权重、风险阈值
- `database.py` — SQLite + aiosqlite, `init_db()` 自动建表

### 关键模块

- `core_engine/polarization_sim.py` — 结构张量梯度法 + Malus定律，生成四通道偏振
- `core_engine/reconstructor.py` — RDN残差稠密网络 (4→16→16→4, 12 blocks, 6 layers, ~0.6M参数)
- `core_engine/enhancement.py` — I_enh v2: `S0*(1+α-γ·DoLP+β·|sin(2·AoP)|·DoLP)`
- `core_engine/inference.py` — YOLOv8s 封装，95类 LifeWatch 藻种
- `core_engine/config.py` — 95类名、风险等级映射 (high/medium/low)、阈值
- `core_engine/quality.py` — Q 质量评分 (DoLP对比度+信噪比+动态范围)

### 后端路由

| 路由 | 说明 |
|------|------|
| `POST /api/v1/detect` | 单图检测 |
| `POST /api/v1/detect/batch` | 批量检测 (最多50张) |
| `GET /api/v1/dashboard/stats` | 仪表板统计 |
| `GET/POST/DELETE /api/v1/history` | 检测历史CRUD |

### 前端

`frontend/index.html` — 6 页面 SPA (首页/检测/历史记录/仪表板/设备管理/人工复核)。
文件夹选择: `webkitdirectory` input + 拖放递归遍历。Chart.js 4.4.0 CDN。

### 依赖

`requirements.txt` 使用灵活的下限版本 (如 `torch>=2.0.0`)，与 `algae_guardian` 的固定版本策略不同。`run.bat` 会自动运行 `pip install -r requirements.txt` 当检测到缺失导入时。

### 模型权重

- `code/algae_image_v1/weights/rdn_polarization.pth` — RDN, PSNR 62.46dB @ epoch 97 (~2.5MB)
- `code/algae_image_v1/weights/best.pt` — YOLOv8s LifeWatch 95类, mAP50 84.7% (~22MB)

### 测试

```bash
cd e:/code/algaeimage/code/algae_image_v1
python -m pytest tests/test_pipeline.py -v   # 核心引擎 (5 test classes)
python -m pytest tests/test_frontend.py -v   # 前端HTML/JS结构 (2 test classes)
```

`conftest.py` 提供会话级 RDN 和 YOLO 模型加载夹具。需要 torch/ultralytics 的测试仅在 conda ican 环境下通过。

---

## 一之补充、algae_image_v2 — V2.0 产品（当前主线）

V2 面向 FMPD 5 类明场显微图像，管线更轻（跳过 RDN），已封装 Windows exe。**当前阶段: 样机演示**（相机直连 + 实时检测 + 前端轮询）。

**2026-06-08 前端重构**: 原生 HTML/CSS/JS → Vue3 + Vite + Element Plus + ECharts（带管线可视化）。
**2026-06-11 样机演示**: 海康 MV-CA013-20GC SDK 直连、实时采集→检测→前端轮询全链路贯通。

### 启动

Windows（需要 GPU + conda ican）:
```bash
cd e:/code/algaeimage/code/algae_image_v2
# Bash 中 conda activate 无效，用完整 Python 路径:
"A:/Anaconda_envs/envs/ican/python.exe" desktop_launcher.py
# 或: "A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# 或: 双击 run.bat
```

macOS（仅前端开发 + API 测试，无需 conda ican）:
```bash
cd frontend && npm install && npm run dev    # Vite dev server (port 5173)
python -m pytest tests/test_api.py -v        # API 测试不依赖 torch/cv2
```

访问: `http://localhost:8000/docs` (API), `http://localhost:8000/app/` (前端生产) 或 `http://localhost:5173/` (Vite dev)

### 处理管线（不可变更顺序）

```
RGB原图 → 结构张量偏振模拟 → RDN偏振重建 → I_enh v2增强 → YOLOv8s检测 → 风险预警(5类FMPD)
```

- **结构张量 + RDN 强绑定**: V2 默认 `SKIP_RDN=False`（`core_engine/config.py`），结构张量模拟物理噪声需要 RDN 去噪。RDN PSNR 62.46dB，V1 成熟权重
- **5 类 FMPD**: Woronichinia / Spiroides / Dinobryon / Other-phytoplankton / Non-phytoplankton
- **默认模型**: YOLOv8s（mAP50 73.9%, train=val）/ 备选 v8l（mAP50 49.6%, 80/20 真实划分）
- **速度控制**: `PIPELINE_MAX_WIDTH=1024`（`core_engine/config.py`），超过此宽度的图片自动缩放，避免 RDN 在全分辨率下计算爆炸（2080px → 317s, 1024px → 3.6s）

### 架构

```
frontend/ (Vue3 + Vite + Element Plus + ECharts, npm build)
    ↓ HTTP REST (JSON + base64 管线中间结果)
backend/ (FastAPI 薄层: 路由 + 参数校验 + SQLite持久化)
    ↓ import
core_engine/ (纯Python库, 零框架依赖: numpy/PyTorch/cv2)
```

**前端技术栈**: Vue3 (Composition API) + Vite 6 + Element Plus 2.9 + ECharts 5.6 + Pinia + Vue Router 4 + Axios。
Vite dev server 自动代理 `/api` 和 `/static` 到 `127.0.0.1:8000`。
旧前端（原生 HTML/CSS/JS）移至 `frontend_legacy/`。

**ECharts 注意**: ECharts 5.x 是树摇架构，必须在入口显式注册 CanvasRenderer + 图表类型 + 组件。
当前 `src/main.js` 已注册 CanvasRenderer, PieChart, BarChart, Grid/Tooltip/Legend/Title。

### 后端路由

| 路由 | 说明 |
|------|------|
| `POST /api/v1/detect` | 单图检测 |
| `POST /api/v1/detect/batch` | 批量检测 (最多50张) |
| `POST /api/v1/detect/visualize` | **单图检测 + 5步管线可视化**（返回 base64 中间结果） |
| `GET /api/v1/detect/latest?n=10` | **实时轮询** — 最近 N 条检测结果（无 base64） |
| `GET /api/v1/detect/stream-status` | **采集状态** — active/fps/帧数/运行时间 |
| `POST /api/v1/detect/stream/start?exposure_us=5000` | **启动采集** — 一键启动相机 SDK 直连，可调曝光 (μs) |
| `POST /api/v1/detect/stream/stop` | **停止采集** — 停止相机并清理资源 |
| `POST /api/v1/detect/stream/start-video` | **启动视频流** — 用视频文件替代相机作为检测源 |
| `POST /api/v1/detect/stream/stop-video` | **停止视频流** |
| `GET /api/v1/detect/video-list` | **视频列表** — 扫描 `video/` 目录返回可用 mp4 |
| `GET /api/v1/detect/video-status` | **视频流状态** |
| `GET /api/v1/dashboard/stats` | 仪表板统计 |
| `GET/ DELETE /api/v1/history` | 检测历史 CRUD |

`/detect/visualize` 由 `PipelineRunner.run_with_visualization()` 驱动，返回 5 个 VizStep（RGB原图→偏振模拟→Stokes参数→I_enh增强→检测结果），每步含 base64 data URI 图像。
对应 Pydantic schemas: `VizStep`, `VizDetectResponse`（`backend/app/schemas.py`）。

### 前端页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 | 管线概览 + 功能卡片 |
| `/detect` | 手动检测 | 拖拽上传 + 5步管线可视化 + 结果表格 + ECharts 图表 |
| `/detect/live` | **实时监测** | 一键启动相机 + 曝光滑块 → 双栏实时展示（原始图 + YOLO标注） |
| `/history` | 历史记录 | 分页表格 + 3s 自动轮询新记录 |
| `/dashboard` | 数据统计 | StatsCards + 饼图 + 柱状图 |

### exe 打包（PyInstaller onedir）

- **入口**: `desktop_launcher.py`（启动 uvicorn + 自动打开浏览器）
- **构建**: `pyinstaller AlgaeImageV2.spec --clean --noconfirm`（`*.spec` 在 `.gitignore` 中排除）
- **路径约定**: 所有文件系统路径必须用 `resource_path()`（`backend/app/config.py`），frozen 时回退到 `sys._MEIPASS`
- **stdout 修复**: `desktop_launcher.py` 将 None stdout/stderr 重定向到 `os.devnull`
- **前端离线**: dist/ 构建产物纳入 git（force-add），打包 exe 时无需 Node.js
- **产物**: `dist-release/AlgaeImageV2/AlgaeImageV2.exe`

### 模型权重

- `code/algae_image_v2/weights/best_v8l.pt` — YOLOv8l FMPD 5类, mAP50 42.9% (~88MB)
- `code/algae_image_v2/weights/best_v8s.pt` — YOLOv8s FMPD 5类, mAP50 73.9% (~22MB)
- `code/algae_image_v2/weights/best.pt` — YOLOv8s 95类 LifeWatch (V1 兼容用)
- `code/algae_image_v2/weights/rdn_polarization.pth` — RDN PSNR 62.46dB (V2 不使用)

### 样机演示流程（2026-06-12 新增）

相机直连 + 实时检测 + 前端轮询，全链路贯通。

**启动（3 步）**:
```bash
# 1. 启动后端
cd e:/code/algaeimage/code/algae_image_v2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2. 启动相机采集（5fps）
python camera_grabber.py --fps 5

# 3.  打开浏览器 → http://localhost:8000/app/detect → 点击导航栏"实时监测"
```

**架构**:
```
相机 SDK callback → numpy RGB → JPEG → POST /api/v1/detect/visualize
→ core_engine 管线 → stream_state.add_result()
→ GET /api/v1/detect/latest (2s 轮询) → Vue3 前端自动刷新
```

**数据流三组件**:
| 组件 | 文件 | 说明 |
|------|------|------|
| SDK 采集器 | `camera_grabber.py` | ctypes 回调→numpy→HTTP POST，节流 5fps |
| AVI 回放 | `video_grabber.py` | cv2 读 AVI 模拟相机，无硬件测试用 |
| 内存缓冲 | `backend/app/services/stream_state.py` | 线程安全，`threading.Lock` 保护，最近 200 条 |

**新增后端端点**:
| 路由 | 说明 |
|------|------|
| `GET /api/v1/detect/latest?n=10` | 最近 N 条检测结果（轻量，无 base64） |
| `GET /api/v1/detect/stream-status` | 采集状态（active, total_frames, effective_fps） |

**前端实时监测**: 导航栏 `el-switch` → Pinia store (`useDetectStore`) → `setInterval` 2s 轮询。全局状态跨组件共享（App.vue + DetectPage.vue）。

### 相机 SDK（海康 MV-CA013-20GC）

- **型号**: MV-CA013-20GC, GigE 1.3MP 彩色
- **SDK**: Python ctypes 封装，`A:\Program Files\MVS\Development\Samples\Python\MvImport`
- **DLL**: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\MvCameraControl.dll`
- **关键**: `import` SDK 之前必须 `os.environ["PATH"]` 加入 DLL 目录（`WinDLL` 模块级加载早于 `os.add_dll_directory`）
- **独占**: SDK 与 MVS 客户端不能同时访问相机（`OpenDevice` 错误码 `0x80000203`）
- **枚举**: `MV_CC_EnumDevices` → 169.254.82.254（直连 GigE，无 DHCP 时的 link-local 地址）
- **曝光控制**: `CameraController.start(exposure_us=5000)` 自动设置 `ExposureAuto=Off` + `ExposureTime`（μs）。前端 `el-slider` 范围 100–50000μs（step 100），运行时禁用

### 已知坑点

- **实时监测不刷新**: `v-model` + `@change="toggleLiveMode"` 双重触发 → 开关来回翻。修复: 去 `@change`，用 `watch(liveMode)` 替代
- **停止按钮无效**: `store.stop()` API 调用失败时状态不重置 → UI 卡死。修复: try/catch 包裹 API 调用，`isStreaming`/`streamMode` 始终重置
- **切 Tab 后状态丢失**: `LiveMonitor.vue` 本地 `state` ref 与 store 断开同步，组件重挂载后停止按钮灰掉。修复: `onMounted` 检查 `store.isStreaming` 恢复状态；Pinia store 测试见 `frontend/src/__tests__/detect-store.test.js`
- **端口残留**: `taskkill` 后端口可能被 `TIME_WAIT` 占用 120s。换端口或用 `SO_REUSEADDR`
- **history.db 文件锁**: Windows 下 uvicorn 异常退出后文件可能被系统进程锁死。若无法删除，改名绕过
- **Bash 中 conda 不可用**: Git Bash 无法 `conda activate`，始终用完整路径 `"A:/Anaconda_envs/envs/ican/python.exe"`
- **SPA fallback**: FastAPI `StaticFiles(html=True)` 不支持子路径。需显式 `@app.get("/app/{full_path:path}")`
- **npm 不在 bash PATH**: 前端构建需通过 Python `subprocess` 调用，并在 env 中设 `PATH=A:\Program Files\nodejs`
- **前端构建产物 (dist/) 在 .gitignore 中**: 如需更新生产部署的静态文件，force-add: `git add -f dist/`

### 测试（分层）

| 测试文件 | 环境要求 | 说明 |
|----------|----------|------|
| `tests/test_api.py` | **无**（macOS 可运行） | 7 个 API 测试，FastAPI TestClient + mock pipeline |
| `tests/test_pipeline.py` | conda ican + torch/cv2 | 核心引擎集成测试 |
| `tests/test_frontend.py` | conda ican | 前端 HTML/JS 结构测试（针对旧前端） |
| `frontend/src/__tests__/detect-store.test.js` | node + vitest | Pinia store 流生命周期测试（停止/轮询/重挂载），6 tests |

```bash
python -m pytest tests/test_api.py -v              # macOS/Windows 均可
python -m pytest tests/test_api.py -v -k "200"     # 单个测试筛选
cd frontend && npm test                             # vitest 前端单元测试
cd frontend && npm run dev                          # 前端热重载开发
cd frontend && npm run build                        # 生产构建 → dist/
```

**Vitest 前端测试**: `vitest.config.js`（jsdom + `@vitejs/plugin-vue`），setup 文件 mock `@/api` 避免 axios 在 jsdom 崩溃。运行前需 `cd frontend && npm install`。

---

## 二、algae_guardian — 研究项目

### 启动

```bash
cd e:/code/algaeimage/code/algae_guardian
python run.py                # 初始化数据库 + 加载模型
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问: `http://localhost:8000/docs`, `http://localhost:8000/app/` (新前端), `http://localhost:8000/static/index.html` (旧面板)

### 处理管线

```
RGB原图 → 偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh增强 → YOLO检测 → 融合预警
```

### 模块结构

- `image_processing/` — 偏振处理、增强、质量评估、评估图表
- `ml/` — 机器学习 (RDN重建、YOLO检测、6类藻种配置、时序追踪)
- `backend/` — FastAPI + SQLite/aiosqlite WAL模式, 3表4路由模块
- `cloud_training/` — 云服务器训练脚本 (数据准备、传输、训练、监控, 27个.py文件)
- `tests/` — 管线测试、批量处理、推理脚本

### 模型权重

- `ml/models/rdn_polarization.pth` — RDN偏振重建 (PSNR 62.46dB @ epoch 97)
- `ml/models/algae_detection.pt` — YOLOv8n-P v0.9 (~6.6MB, 独立文件非符号链接)
- `ml/models/yolov8l.pt` — YOLOv8l升级 (mAP50=0.429)

### 关键数据目录

**FMPD 数据集** (293张FlowCam真实显微图像):
- 原始TIFF: `data/download/extracted/dataset/dataset/*.tif`
- 偏振模拟 (.npz): `data/download/extracted/dataset/polarized/polarization/`
- 偏振预览 (Stokes/AoP/DoLP): `data/download/extracted/dataset/polarized/preview/`
- 增强预览: `data/download/extracted/dataset/polarized/enhanced_preview/`
- RDN输出 (I_enh): `data/fmpd_rdn_output/images/`
- YOLO预测 (已画框): `data/yolo_results/predictions/`

### 平台静态资源

- 新平台页面: `frontend/index.html` (挂载到 `/app/`)
- 旧监控面板: `backend/static/index.html` (挂载到 `/static/`)
- 平台图片: `pic/` 目录 (映射到 `E:/code/algaeimage/pic/`)
- 技术文档: `项目文书/藻影知微_0508.md`

### 数据闭环

- 人工复核 → POST `/api/v1/review/submit` → `backend/data/reviewed/{id}/`
- 加入训练集 → POST `/api/v1/review/approve/{id}` → `backend/data/training_pool/{id}/`
- 图片通过 `/pic/` 挂载提供

---

## 三、其他代码目录

### Polar_sim_0520 — 结构张量实验 (V1 算法来源)

当前 V1 产品管线的算法原型。关键文件:
- `image_processing/polarization.py` — 偏振核心工具函数
- `image_processing/polarization_sim.py` — 结构张量 + HSV 两种偏振模拟方法
- `ml/reconstructor.py` — RDN 重建网络
- `docs/pipeline_design.md` — 结构张量管线设计文档
- `auto_train_eval.py` — 自动化训练+评估驱动脚本

### Polar_sim_0522 — HSV 实验 (已废弃) + Docker 环境

HSV 色彩空间偏振模拟，性能远低于结构张量。但保留了**完整的 Docker 化训练环境**:
- `Dockerfile` — NVIDIA PyTorch 基础镜像, CUDA 12.1, 清华 pip 镜像源
- `docker-compose.yml` — GPU 透传, 8GB shm, 挂载 `E:/code/algaeimage/datasets` 和 `E:/code/algaeimage/results`
- `deploy/run_all.py` — 全流程部署入口

### SPDRDN — 原始 RDN 研究 (独立 git 仓库)

嵌套的独立 git 仓库，包含 RDN 网络原型。4 个偏振分支 (AOP/DOCP/DOLP/DOP)，各有独立 train/test/prepare 脚本。含 MATLAB 评估脚本 (`Full_Stokes_parameters.m`, `my_ssim.m`) 和 HDF5 格式训练数据。有自己独立的 `.claude/` 配置。

---

## 四、仓库级工具脚本

根目录下的 Python 脚本用于云训练管理:

| 脚本 | 用途 |
|------|------|
| `check_yolo_training.py` | 通过 SSH 监控云端 YOLO 训练 (paramiko) |
| `download_previews.py` | 下载训练预览图 (results.png, batch samples) |
| `download_results_20260522.py` | 批量递归下载训练结果 |
| `plot_metrics.py` | 从 results.csv 生成训练曲线图 |
| `tmp_download_500.py` | 随机选取 500 张 LifeWatch 样本并打包下载 |
| `tmp_download_fmpd.py` | 将 FMPD.zip (2.1GB) 从 Zenodo 下载到云服务器 |

## 五、云训练监控

云训练监控任务已移除（`scheduled_tasks.json` 当前为空）。如需恢复，使用 `CronCreate` 工具重新配置。

---

## 项目基础设施

- **无 CI/CD** — 无 GitHub Actions、Jenkins 等配置
- **无 lint/formatter** — 无 ruff、black、flake8 配置，Python 代码无统一风格约束
- **GitHub CLI 可用** — `gh` 已安装，可用于 PR/Issue 操作
- **Git LFS** — 追踪 `*.tif *.zip *.pth *.pt *.npz *.mp4`
- **`.claude/rules/`** — 按路径生效的条件规则：`frontend.md`、`backend.md`、`core-engine.md`、`python-general.md`

---

## 共享设计决策

- **I135 不是 I0/I90 平均**: 4个偏振通道全部用同一 Malus 物理模型独立计算，保证 S2 = I45 - I135 有物理意义
- **DoFP偏振相机**: 采集 I0/I45/I90 三个方向，S0 = I0+I90, S1 = I0-I90, S2 = I45-I135
- **训练数据增强**: 藻类区域 (green_ratio>0.33) 额外增加30%偏振差异
- **结构张量法优于HSV法**: 结构张量 YOLOv8s mAP50=84.7% vs HSV YOLOv8l mAP50=37.9%
- **数据量是当前瓶颈**: FMPD 仅293张，不足以支撑大模型

## YOLO训练历史

- **v8s LifeWatch**: 95类, mAP50=0.847, 已在 algae_image_v1 中使用 (结构张量法)
- **v8s Baseline** (algae_guardian): mAP50=0.739 (train=val评估, 虚高), best @epoch 233
- **v8l Upgrade** (algae_guardian): 80/20分, mAP50=0.429, mAP50-95=0.197, best @epoch 110
- 最佳类别: Woronichinia 0.659, Spiroides 0.610; 最差: Non-phytoplankton 0.162

## 重要提示

- **Conda 环境**: `ican`, 路径 `A:\Anaconda_envs\envs\ican`, Python 3.11
- **模型权重和数据不在 git 中** — `.gitignore` 排除了 `*.pt`, `*.pth`, `*.tif`, `*.zip`, `*.npz` 及 `data/`, `output/` 目录。新克隆需要单独获取权重文件。
- **当前分支 `HSV`** 上 `code/algae_image_v1/` 的全部文件 (backend/, core_engine/, frontend/, tests/, docs/) 尚未 git 提交。
- `code/SPDRDN/` 是嵌套的独立 git 仓库，有自己的 `.claude/` 配置。
