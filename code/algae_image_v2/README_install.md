# 藻类检测 V2 — 安装与部署指南

> **版本**: 2.0  
> **最后更新**: 2026-07-05  
> **适用场景**: FMPD 5 类明场藻类显微图像检测（含相机直连实时监测）

---

## 目录

1. [软件概述](#1-软件概述)
2. [系统要求](#2-系统要求)
3. [完整文件清单](#3-完整文件清单)
4. [安装步骤](#4-安装步骤)
5. [启动与使用](#5-启动与使用)
6. [相机配置（可选）](#6-相机配置可选)
7. [常见问题](#7-常见问题)
8. [附录：Docker 方案](#8-附录docker-方案待实现)

---

## 1. 软件概述

### 1.1 功能

藻类检测 V2 是面向 FMPD（FlowCam Micro-Polarization Detection）5 类明场显微图像的智能检测系统，支持：

- **手动检测**: 上传单张/批量图片 → 5 步管线可视化 → 风险预警
- **实时监测**: 海康 MV-CA013-20GC 工业相机直连 → 连续采集 → 自动检测 → 前端轮询
- **视频回放**: AVI 视频文件替代相机 → 模拟实时检测（无需硬件）
- **数据管理**: 检测历史 CRUD、仪表板统计（饼图 + 柱状图）、人工复核闭环

### 1.2 处理管线（不可变更顺序）

```
RGB原图 → 结构张量偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh v2增强 → YOLOv8s/v8l检测 → 风险分级
```

### 1.3 5 类 FMPD 藻种

| 英文名 | 中文名 | 风险等级 |
|--------|--------|----------|
| Woronichinia | 沃氏藻 | **高** |
| Spiroides | 螺旋藻 | **高** |
| Dinobryon | 锥囊藻 | **中** |
| Other-phytoplankton | 其他浮游植物 | **低** |
| Non-phytoplankton | 非浮游植物 | — |

### 1.4 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 (Composition API) + Vite 6 + Element Plus 2.9 + ECharts 5.6 + Pinia |
| 后端 | FastAPI 0.136 + Uvicorn 0.47 |
| 算法 | PyTorch 2.11 + Ultralytics 8.4 (YOLOv8s/v8l) + NumPy + OpenCV |
| 数据库 | SQLite (aiosqlite 异步驱动) |
| 模型 | YOLOv8s (mAP50 73.9%) / YOLOv8l (mAP50 42.9%) + RDN (PSNR 62.46dB) |

---

## 2. 系统要求

### 2.1 最低配置

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows 10/11 x64 |
| **Python** | 3.11 (通过 Conda / Miniconda 管理) |
| **内存** | ≥ 8 GB |
| **磁盘** | ≥ 5 GB (conda 环境 ~2GB + 权重 129MB + 运行时数据) |
| **GPU** | 推荐 NVIDIA ≥ 6GB VRAM + CUDA 12.x |
| **CPU 回退** | 可用但极慢（单张约 10-30× 耗时），不推荐生产使用 |

### 2.2 可选硬件

| 硬件 | 用途 | 备注 |
|------|------|------|
| 海康 MV-CA013-20GC | 实时相机直连 | GigE 接口，1.3MP 彩色 |
| MVS SDK 3.x+ | 驱动上述相机 | 仅 Windows x64，需单独安装 |

---

## 3. 完整文件清单

### 3.1 目录总览

```
algae_image_v2/
├── run.bat                    # 一键启动脚本（双击运行）
├── setup.bat                  # 一键安装脚本（首次运行）
├── environment.yml            # Conda 环境定义（精确依赖版本）
├── requirements.txt           # Pip 依赖（备选，供非 conda 环境使用）
├── desktop_launcher.py        # 桌面启动入口（PyInstaller 打包用）
├── README_install.md          # 本文件
│
├── backend/                   # FastAPI 后端服务
│   └── app/
│       ├── main.py            # 应用入口：生命周期管理、静态文件挂载、SPA路由
│       ├── config.py          # 部署级配置：路径常量、resource_path()、网络设置
│       ├── database.py        # SQLite 数据库初始化 (4表) + 连接工厂
│       ├── routes.py          # 核心路由：检测、批量检测、管线可视化、流控制
│       ├── routes_data.py     # 数据路由：仪表板统计、历史CRUD、设备管理、人工复核
│       ├── schemas.py         # Pydantic Schema 重导出 (→ shared/schemas.py)
│       └── services/
│           ├── pipeline.py    # 管线编排器 PipelineRunner — 全5阶段流程控制
│           ├── camera.py      # 相机控制器 — MVS SDK 封装 + 后台工作线程
│           ├── video.py       # 视频控制器 — AVI 文件模拟相机流
│           └── stream_state.py # 内存缓冲 — 线程安全，最近200条实时结果
│
├── core_engine/               # 核心算法引擎（零框架依赖，纯 Python 库）
│   ├── config.py              # 算法级配置：FMPD 5类映射、风险等级、I_enh 参数、模型元数据
│   ├── polarization_sim.py    # 结构张量偏振模拟 — RGB→I0/I45/I90/I135 (Malus 定律)
│   ├── hsv_polarization.py    # HSV 偏振模拟 — 备选方案 (Yan et al., Photonics 2024)
│   ├── reconstructor.py       # RDN 残差稠密网络 — 4通道偏振去噪 (~0.6M 参数)
│   ├── enhancement.py         # I_enh v2 去散射增强 — Stokes → 增强图
│   ├── inference.py           # YOLO 检测封装 — 模型加载/切换/推理/结构化输出
│   └── quality.py             # Q 质量评分 — DoLP对比度+信噪比+动态范围
│
├── shared/
│   └── schemas.py             # 共享 Pydantic 模型 — API 数据结构的单一事实来源
│
├── frontend/
│   └── dist/                  # Vue 前端构建产物（生产部署用，约 2.2MB, 21个文件）
│       ├── index.html         # SPA 入口 HTML
│       └── assets/            # JS/CSS 分块文件
│
├── weights/                   # ⚠️ 模型权重（约 129MB，需单独传输，不在 git 中）
│   ├── best_v8l.pt            # YOLOv8l — 高精度模型，mAP50 42.9%, 83.6MB
│   ├── best_v8s.pt            # YOLOv8s — 轻量模型，mAP50 73.9%, 21.5MB
│   ├── best.pt                # YOLOv8s 95类 LifeWatch (V1 兼容用), 21.5MB
│   └── rdn_polarization.pth   # RDN 偏振去噪网络, PSNR 62.46dB, 2.4MB
│
├── camera_grabber.py          # 独立相机采集脚本（需 MVS SDK + 相机硬件）
├── video_grabber.py           # 独立视频回放脚本（AVI → 模拟相机，无需硬件）
│
├── backend/data/              # ⚠️ 运行时数据目录（自动创建）
│   ├── history.db             # SQLite 检测历史数据库
│   ├── uploads/               # 用户上传的原始图片
│   └── results/               # 检测结果标注图
│       └── live/              # 实时监测帧缓存
│
└── tests/                     # 测试套件
    ├── conftest.py            # Pytest 夹具 (RDN + YOLO 会话级模型加载)
    ├── test_api.py            # API 集成测试 (FastAPI TestClient, 不依赖 torch/cv2)
    └── test_pipeline.py       # 核心引擎测试 (需 conda ican)
```

### 3.2 每个文件的功能详解

#### 启动与配置脚本

| 文件 | 大小 | 功能 |
|------|------|------|
| `run.bat` | ~3KB | **一键启动脚本**。自适应查找 Python/conda → 检查权重 → 验证依赖 → 启动 uvicorn → 打开浏览器。可在任何安装了 conda ican 的 Windows 机器上运行。 |
| `setup.bat` | ~3KB | **一键安装脚本**。检测 conda → 创建/更新 ican 环境 → 安装 pip 依赖 → 检查权重 → 创建运行时目录。首次部署或环境修复时运行。 |
| `environment.yml` | ~2KB | **Conda 环境定义文件**。精确锁定 Python 3.11 + PyTorch 2.11 (CUDA 12.6) + 所有依赖版本。跨机器一致复现的基石。 |
| `requirements.txt` | 221B | **Pip 依赖清单**（灵活下限版本）。供非 conda 环境使用，conda 用户优先用 environment.yml。 |
| `desktop_launcher.py` | 1.1KB | **桌面启动入口**。PyInstaller 打包的入口点：启动 uvicorn (127.0.0.1:8000) + 2 秒后打开浏览器。修复了 PyInstaller `console=False` 模式的 stdout None 问题。 |

#### 后端 (backend/app/)

| 文件 | 大小 | 功能 |
|------|------|------|
| `main.py` | 4.6KB | **FastAPI 应用工厂**。lifespan handler 加载 RDN+YOLO 模型、初始化相机/视频控制器。挂载 4 个静态目录 (`/static/results`, `/static/uploads`, `/static/live`, `/assets`)。配置 CORS 允许所有来源。SPA fallback 路由 `/app/{full_path}`。 |
| `config.py` | 1.7KB | **部署级配置常量**。`resource_path()` — PyInstaller frozen 与 dev 模式兼容的路径解析。`BASE_DIR`, `WEIGHTS_DIR`, `YOLO_WEIGHTS`, `RDN_WEIGHTS`, `DATA_DIR`, `DB_PATH`, `HOST=0.0.0.0`, `PORT=8000`。 |
| `database.py` | 2.7KB | **SQLite 数据库层**。`init_db()` 自动建 4 表：`detection_history`(检测记录), `batch_tasks`(批量任务), `devices`(设备管理), `reviewed_records`(人工复核)。`get_db()` 异步连接工厂 (aiosqlite, WAL 模式)。 |
| `routes.py` | 18.8KB | **核心检测路由**。包含 11 个端点：`POST /detect`(单图), `POST /detect/batch`(批量≤50张), `POST /detect/visualize`(单图+管线可视化), `GET /detect/latest`(实时轮询), `POST /detect/stream/start|stop`(相机采集), `POST /detect/stream/start-video|stop-video`(视频回放), `GET /detect/video-list|video-status`。 |
| `routes_data.py` | 12.5KB | **数据管理路由**。包含 10+ 端点：`GET /dashboard/stats`, `GET|DELETE /history`, `GET|POST|PUT|DELETE /devices`, `GET|POST /review`。不含 ML 依赖，可独立测试。 |
| `schemas.py` | 1KB | **Schema 重导出**。将 `shared/schemas.py` 中的 Pydantic 模型统一从此处导出，供路由文件引用。 |
| `services/pipeline.py` | 12KB | **管线编排器 PipelineRunner**。核心类：持有 YOLO 模型引用 → `run()` 执行完整 5 阶段管线 → `run_with_visualization()` 返回每步中间结果 (base64)。支持 ndarray 直传（跳过文件IO）和 文件路径两种输入。 |
| `services/camera.py` | ~23KB | **MVS SDK 相机控制器**（单例）。自动探测 MVS SDK 安装路径 → 初始化 SDK → 枚举 GigE 设备 → 注册帧回调 → 后台工作线程（出队→管线→保存 JPEG→stream_state→批量写 DB→图像裁剪）。支持曝光时间调节 (100–50000μs)。 |
| `services/video.py` | 9.9KB | **视频文件流控制器**（单例）。OpenCV 读取 AVI → 节流 (fps) → 管线处理 → stream_state。支持循环播放 (`--loop`) 和单次播放 (`--once`)。无相机时的替代方案。 |
| `services/stream_state.py` | 2.7KB | **内存结果缓冲**（线程安全）。`threading.Lock` 保护，最近 200 条结果。追踪总帧数/有效 fps/运行时间。前端 2 秒轮询的数据来源。 |

#### 核心算法引擎 (core_engine/)

| 文件 | 大小 | 依赖 | 功能 |
|------|------|------|------|
| `config.py` | 3.9KB | 无 | **算法配置**。FMPD 5 类 ID→名称→中文名→风险等级映射。I_enh v2 增强参数 (α=0.3, β=0.5, γ=0.2)。管线宽度限制 (1024px)。模型元数据 (v8l/v8s 路径/输入尺寸/类别数)。风险颜色映射。 |
| `polarization_sim.py` | 4KB | numpy, cv2 | **结构张量偏振模拟**。Sobel 梯度 → 结构张量 → 各向异性+方向 → Malus 定律 (cos²θ, 对应 I0/I45/I90/I135)。所有 4 通道独立计算保证 S2=I45−I135 物理意义。 |
| `hsv_polarization.py` | 6.2KB | numpy, cv2 | **HSV 偏振模拟**（备选）。Yan et al. (2024) 方法：S 通道→DoLP, H 通道→AoP, V 通道→S0 → 4 通道。含批量处理和预览网格生成。性能远低于结构张量法。 |
| `reconstructor.py` | 6.3KB | torch, numpy | **RDN 残差稠密网络**。4→16→16→4 通道，12 个 RDB 块，每块 6 层 Conv+ReLU，~0.6M 参数。`load_rdn_model(weights_path)` — 带权重安全加载。`reconstruct(model, pol_images)` — 输入 (4,H,W) ndarray → 输出 (4,H,W)。 |
| `enhancement.py` | 3.1KB | numpy | **I_enh v2 去散射增强**。4 通道 → Stokes (S0/S1/S2) → DoLP/AoP → `I_enh = Norm(S0 × (1 + α − γ·DoLP + β·|sin(2·AoP)|·DoLP))`。3 通道合成返回增强图。 |
| `inference.py` | 5.2KB | torch, ultralytics, numpy | **YOLO 检测封装**。`load_yolo()`—可选 v8s/v8l，`load_yolo_by_key()`—字符串切换，`detect()`—灰度→3通道→推理→结构化 DetectionItem 列表。自动关联风险等级。 |
| `quality.py` | 3.5KB | numpy | **Q 质量评分**。加权公式：DoLP 对比度 (40%) + 信号强度 (20%) + 动态范围 (20%) − 噪声 (10%) − 均值散布 (10%)。标签：Good (≥0.7), Fair (≥0.4), Poor。 |

#### 独立采集脚本

| 文件 | 大小 | 依赖 | 功能 |
|------|------|------|------|
| `camera_grabber.py` | ~12KB | MVS SDK, cv2, requests | **独立相机采集**。连 MVS SDK → 枚举设备 → 注册回调 → HTTP POST (base64 JPEG) → `/api/v1/detect/visualize`。支持 `--fps`、`--duration`、`--once`、`--base-url`。独立于 FastAPI 进程运行。 |
| `video_grabber.py` | 4.4KB | cv2, requests | **独立视频回放**。OpenCV 读 AVI → 逐帧 POST → `/api/v1/detect/visualize`。支持 `--fps`、`--loop`、`--once`。无需相机硬件。 |

#### 前端 (frontend/dist/)

| 文件/目录 | 大小 | 说明 |
|-----------|------|------|
| `index.html` | 446B | Vue SPA 入口，含 `<div id="app">` 挂载点 |
| `assets/index-DL0MVZf1.js` | 1.71MB | 主 vendor 包：Vue 3 + Element Plus 2.9 + ECharts 5.6 |
| `assets/index-vSRnZER0.css` | 358KB | 主样式包：Element Plus 主题 + 自定义样式 |
| `assets/HomePage-*.js` | 16KB | 首页 — 管线概览 + 功能卡片 |
| `assets/LiveMonitor-*.js` | 8KB | 实时监测页 — 双栏展示原始图+YOLO标注 + 曝光滑块 |
| `assets/DetectPage-*.js` | 5.5KB | 手动检测页 — 拖拽上传 + 5步管线可视化 |
| `assets/DashboardPage-*.js` | 3.2KB | 数据统计页 — StatsCards + ECharts 图表 |
| `assets/HistoryPage-*.js` | 3.2KB | 历史记录页 — 分页表格 + 3s 自动轮询 |
| 其他 chunk | < 5KB each | 设备管理、人工复核、ReviewPage、DevicesPage |

#### 共享模块

| 文件 | 大小 | 功能 |
|------|------|------|
| `shared/schemas.py` | 4.4KB | **API 数据模型的单一事实来源**。定义 `DetectionItem`, `SingleDetectResponse`, `BatchDetectResponse`, `VizStep`, `VizDetectResponse`, `LatestResult`, `StreamStatusResponse`, `StatsResponse`, `HistoryItem`, `DeviceInfo`, `ReviewItem`, `ReviewSubmitRequest` 等 Pydantic v2 模型。零 ML 依赖，前后端共享。 |

---

## 4. 安装步骤

### 4.1 方案总览

目标机器部署只需要 3 层，每层有明确的分工：

```
┌─────────────────────────────────────────────────────┐
│ 第 1 层：Miniconda (~80MB)                          │
│   提供 conda 包管理器 + 环境隔离能力                  │
│   下载：https://docs.conda.io/en/latest/miniconda    │
├─────────────────────────────────────────────────────┤
│ 第 2 层：setup.bat（自动）                           │
│   读取 environment.yml → 创建 ican 环境              │
│   → 安装 PyTorch(CUDA) + FastAPI + Ultralytics 等 13 个包 │
│   → 检查模型权重 → 创建运行时目录                     │
├─────────────────────────────────────────────────────┤
│ 第 3 层：run.bat（一键启动）                         │
│   4 级自适应查找 Python → 验证依赖 → 启动服务         │
│   → 自动打开浏览器 → http://localhost:8000/app/      │
└─────────────────────────────────────────────────────┘
```

**为什么用 Miniconda 而不是完整 Anaconda？**

| | Miniconda | Anaconda |
|------|-----------|----------|
| 安装包大小 | ~80 MB | ~3 GB |
| 自带包数量 | 仅 conda + python | 250+ 预装包 |
| 本项目的依赖 | 全部由 environment.yml 指定，不需要预装 | 预装包与本项目无关，浪费空间 |
| 推荐 | ✅ | ❌ |

**为什么 PyTorch 走 conda 的 `pytorch` channel 而不是 pip？**

PyTorch 安装最常出错的地方是 CUDA 版本不匹配。conda 的 `pytorch` channel 提供的是**预编译好 CUDA 12.6 + cudnn 9 的二进制包**，`conda env create` 一条命令自动拉取正确的 CUDA 运行时，不会出现 "装了 CUDA 11.8 的 PyTorch 却只有 CUDA 12 驱动" 这种问题。而 pip 安装 torch 需要手动去 pytorch.org 选 CUDA 版本拼 pip 命令，容易装成 CPU-only。

**为什么 environment.yml 锁定精确版本而 requirements.txt 用下限？**

| 文件 | 版本策略 | 用途 |
|------|----------|------|
| `environment.yml` | `==` 精确锁定 | **目标机器复现** — 保证与原开发机完全相同 |
| `requirements.txt` | `>=` 灵活下限 | **开发机快速修复** — run.bat 发现缺包时自动补装 |

---

### 4.2 获取文件

确保以下内容齐备：

| 来源 | 内容 | 约大小 |
|------|------|--------|
| 项目代码 | 本仓库所有 `.py` / `.bat` / `.yml` / `.txt` / `frontend/dist/` | ~5 MB |
| 模型权重 | `weights/` 下 4 个文件，从原机器拷贝或 Git LFS 拉取 | ~129 MB |

> **注意**：模型权重文件 (`*.pt`, `*.pth`) 不在 git 仓库中（`.gitignore` 排除）。如果用 git clone，需要额外获取。

---

### 4.3 安装 Conda（如尚未安装）

1. 下载 [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (Windows 64-bit)
2. 安装时勾选 **"Add Miniconda to my PATH environment variable"**
3. 安装完成后**重新打开终端**

### 4.4 一键安装（推荐）

```batch
# 双击运行（文件管理器）
setup.bat

# 或在终端中运行
cd /d E:\code\algaeimage\code\algae_image_v2
setup.bat
```

**setup.bat 执行的 5 个步骤：**

```
[1/5] 检查 Python 环境
      ├── 优先找 conda (where conda → 扫描常见安装目录)
      ├── 备选找独立 Python 安装
      └── 都不存在 → 提示安装 Miniconda

[2/5] 创建/更新 ican 环境
      ├── conda env create -f environment.yml
      │      ├── pytorch channel → PyTorch 2.11 + CUDA 12.6 + cudnn 9
      │      ├── conda-forge channel → Python 3.11.11
      │      └── pip → FastAPI 0.136.3, Ultralytics 8.4.48, 等 11 个包
      ├── 约需下载 2-3 GB（首次，耗时取决于网速）
      └── 若环境已存在，自动增量更新 (conda env update --prune)

[3/5] 验证 Python 依赖
      └── python -c "import torch; print(torch.cuda.is_available())"
         确认 PyTorch + CUDA 可用

[4/5] 检查模型权重
      └── 列出 weights/ 目录中缺失的文件

[5/5] 创建运行时目录
      └── backend/data/uploads / results / results/live
```

### 4.5 手动安装（备选）

如果 `setup.bat` 失败，可以逐步手动操作：

```batch
# 1. 创建 conda 环境
conda env create -f environment.yml

# 2. 验证环境
conda activate ican
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')"

# 3. 放入模型权重
# 将 best_v8l.pt, best_v8s.pt, rdn_polarization.pth 复制到 weights\ 目录

# 4. 创建运行时目录
mkdir backend\data\uploads
mkdir backend\data\results
mkdir backend\data\results\live
```

### 4.6 替换模型（可选）

```batch
# 默认使用 YOLOv8l (高精度)
# 如需切换为 YOLOv8s (轻量)，修改 backend/app/config.py：
#   YOLO_WEIGHTS = resource_path("weights/best_v8s.pt")

# 跳过 RDN (V2 默认跳过)
# core_engine/config.py 中设置: SKIP_RDN = True
```

---

## 5. 启动与使用

### 5.1 启动

```batch
双击 run.bat
```

**run.bat 的 4 级自适应 Python 查找逻辑：**

```
第 1 级：CONDA_PREFIX（已激活的 conda 环境）
         └── 如果你在终端中先 conda activate ican，直接复用

第 2 级：PATH 中的 python
         └── where python 找到的任意 Python（conda/系统均可）

第 3 级：扫描常见 conda 安装目录
         └── %USERPROFILE%\miniconda3\envs\ican
             %USERPROFILE%\anaconda3\envs\ican
             C:\ProgramData\miniconda3\envs\ican
             A:\Anaconda_envs\envs\ican  (原开发机路径，向后兼容)

第 4 级：系统 Python
         └── %LOCALAPPDATA%\Programs\Python\Python311\
             C:\Python311\
```

> **设计原因**：原 `run.bat` 硬编码 `A:\Anaconda_envs\envs\ican\python.exe`，换一台机器立刻失效。现在逐级回退：环境变量 → 全局 PATH → 文件系统扫描 → 系统安装，覆盖 99% 的 Windows Python 部署场景。

启动过程：
1. 按上述 4 级顺序找到 Python
2. 验证 `weights\best_v8l.pt` 存在
3. `python -c "import fastapi, uvicorn, torch, ultralytics, cv2"` 快速检查依赖（缺失则自动 pip install）
4. 启动 uvicorn → `http://0.0.0.0:8000`
5. 2 秒后自动打开浏览器 → `http://localhost:8000/app/`

### 5.2 页面功能

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页 | `/` | 管线概览 + 功能卡片导航 |
| 手动检测 | `/detect` | 拖拽上传图片 → 5 步管线可视化 → 检测结果表格 + ECharts 图表 |
| 实时监测 | `/detect/live` | 一键启动相机 → 双栏实时展示（原始图 + YOLO 标注） |
| 历史记录 | `/history` | 分页表格 + 3s 自动轮询新记录 |
| 数据统计 | `/dashboard` | StatsCards + 饼图 + 柱状图 |
| 人工复核 | `/review` | 检测结果复核 → 标记加入训练集 |

### 5.3 API 端点速查

| 方法 | 路由 | 说明 |
|------|------|------|
| `POST` | `/api/v1/detect` | 单图检测 |
| `POST` | `/api/v1/detect/batch` | 批量检测 (≤50张) |
| `POST` | `/api/v1/detect/visualize` | 单图 + 5步管线可视化 (base64) |
| `GET` | `/api/v1/detect/latest?n=10` | 实时轮询 (最近 N 条，无 base64) |
| `GET` | `/api/v1/detect/stream-status` | 采集状态 (active/fps/帧数) |
| `POST` | `/api/v1/detect/stream/start?exposure_us=5000` | 启动相机采集 |
| `POST` | `/api/v1/detect/stream/stop` | 停止相机采集 |
| `POST` | `/api/v1/detect/stream/start-video` | 启动视频回放 |
| `POST` | `/api/v1/detect/stream/stop-video` | 停止视频回放 |
| `GET` | `/api/v1/detect/video-list` | 可用视频列表 |
| `GET` | `/api/v1/dashboard/stats` | 仪表板统计 |
| `GET` | `/api/v1/history` | 检测历史 (分页) |
| `DELETE` | `/api/v1/history` | 清除历史 |

API 交互式文档: `http://localhost:8000/docs`

---

## 6. 相机配置（可选）

### 6.1 硬件要求

- **型号**: 海康机器人 MV-CA013-20GC (GigE, 1.3MP, 彩色)
- **连接方式**: 以太网直连（link-local 地址 169.254.x.x）
- **注意事项**: MVS 客户端与 SDK 不能同时占用设备

### 6.2 安装 MVS SDK

1. 从 [海康机器人官网](https://www.hikrobotics.com/machinevision) 下载 MVS (Machine Vision Software)
2. 安装到默认路径（推荐 `C:\Program Files\MVS`）
3. 验证安装：
   ```batch
   dir "C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\MvCameraControl.dll"
   ```

### 6.3 自定义 SDK 路径

若 MVS 安装位置不在默认盘符（A/C/D/E），设置环境变量：

```batch
set MVS_SDK_PATH=D:\MyTools\MVS
```

或在系统环境变量中永久设置：
```
此电脑 → 属性 → 高级系统设置 → 环境变量 → 新建
变量名: MVS_SDK_PATH
变量值: D:\MyTools\MVS
```

### 6.4 采集流程

```batch
# 终端 1: 启动后端
run.bat

# 终端 2: 启动相机采集（5 fps）
conda activate ican
python camera_grabber.py --fps 5

# 浏览器 → http://localhost:8000/app/detect/live → 打开实时监测开关
```

---

## 7. 常见问题

### Q1: run.bat 提示"未找到 Python"

**原因**: conda 未安装或未加入 PATH

**解决**:
1. 安装 Miniconda → 确保勾选 "Add to PATH"
2. 或手动运行 `setup.bat`，它会搜索常见安装位置
3. 或设置 `PYTHON_EXE` 环境变量指向你的 Python 路径

### Q2: `ImportError: No module named 'torch'`

**原因**: conda 环境未创建或激活失败

**解决**:
```batch
# 检查环境是否存在
conda env list

# 若没有 ican，创建它
conda env create -f environment.yml

# 若存在但损坏，重建
conda env remove -n ican
conda env create -f environment.yml
```

### Q3: GPU 内存不足 (CUDA out of memory)

**解决**:
- 减小 `core_engine/config.py` 中的 `PIPELINE_MAX_WIDTH` (默认 1024)
- 切换为 YOLOv8s 轻量模型：修改 `backend/app/config.py` 中 `YOLO_WEIGHTS` 指向 `best_v8s.pt`
- 回退 CPU 模式（极慢）：确认 `torch.cuda.is_available() == False` 时自动切换

### Q4: 相机连接失败

**常见错误码**:
| 错误码 | 含义 | 解决 |
|--------|------|------|
| `0x80000203` | 设备被占用 | 关闭 MVS 客户端软件 |
| `CreateHandle failed` | SDK 初始化失败 | 检查 GigE 网线连接和防火墙 |
| 找不到 `MvCameraControl.dll` | MVS SDK 未安装 | 安装 MVS 或设置 `MVS_SDK_PATH` 环境变量 |

### Q5: 端口 8000 被占用

```batch
# 查找占用进程
netstat -ano | findstr :8000

# 或修改 backend/app/config.py 中 PORT = 8001
```

### Q6: 权重文件缺失

模型权重不在 git 仓库中（`.gitignore` 排除 `*.pt`, `*.pth`）。需要从原开发机器拷贝或通过 Git LFS 拉取：

```batch
git lfs pull  # 如果仓库使用 LFS 追踪
```

---

## 8. 附录：Docker 方案（待实现）

### 8.1 当前限制

MVS SDK 是 Windows-only 的原生 DLL，无法在 Linux Docker 中运行。相机直连功能必须保留在宿主机。

### 8.2 计划架构

```
[宿主机 Windows]
├── camera_grabber.py (MVS SDK, Windows) ──HTTP POST──┐
├── 浏览器 ──HTTP GET─────────────────────────────────┤
└── Docker Desktop                                     │
     └── [Linux 容器]                                  │
          └── FastAPI + core_engine + YOLO ────────────┘
```

### 8.3 适用场景

- 只做文件检测（不需要相机）的机器 → 完整 Docker 化
- 需要相机 + 检测的机器 → 宿主机跑 camera_grabber.py, 容器跑后端

---

**文档版本**: 1.0  
**维护者**: 52herzee  
**对应分支**: `v2-platform`
