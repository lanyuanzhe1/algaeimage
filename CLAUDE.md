# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概览

本仓库包含藻类显微图像偏振检测的完整研究到产品管线：

| 目录 | 定位 |
|------|------|
| `code/algae_image_v1/` | **V1.0 产品** — 桌面工具，单机运行，当前开发焦点 |
| `code/algae_guardian/` | 研究型项目 — 训练、评估、完整实验 |
| `code/Polar_sim_0520/` | 结构张量管线实验 (mAP50 82.24%)，V1 产品的算法来源 |
| `code/Polar_sim_0522/` | HSV 偏振实验 (mAP50 37.9%，已废弃)，含 Docker 训练环境 |
| `code/SPDRDN/` | RDN 网络原始研究 (独立 git 仓库)，含 MATLAB 评估脚本 |

`docs/` 目录包含 13 份参考文档 (训练总结、交接文档、数据集调查等)。

**当前分支**: `HSV`。`code/algae_image_v1/` 全部文件尚未 git 提交。

---

## 一、algae_image_v1 — V1.0 产品

### 启动

```bash
conda activate ican
cd e:/code/codex/code/algae_image_v1
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# 或双击 run.bat (Windows 一键启动: 自动检查权重文件 + conda 环境 + 依赖)
```

访问: `http://localhost:8000/docs` (API), `http://localhost:8000/app/` (前端)

### 处理管线 (不可变更顺序)

```
RGB原图 → 结构张量偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh v2去散射增强 → YOLOv8s检测(95类)
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

`frontend/index.html` — 5 Tab SPA (检测/历史记录/仪表板 已启用; 设备管理/人工复核 占位)。
文件夹选择: `webkitdirectory` input + 拖放递归遍历。Chart.js 4.4.0 CDN。

### 依赖

`requirements.txt` 使用灵活的下限版本 (如 `torch>=2.0.0`)，与 `algae_guardian` 的固定版本策略不同。`run.bat` 会自动运行 `pip install -r requirements.txt` 当检测到缺失导入时。

### 模型权重

- `weights/rdn_polarization.pth` — RDN, PSNR 62.46dB @ epoch 97 (~2.5MB)
- `weights/best.pt` — YOLOv8s LifeWatch 95类, mAP50 84.7% (~22MB)

### 测试

```bash
cd e:/code/codex/code/algae_image_v1
python -m pytest tests/test_pipeline.py -v   # 核心引擎 (5 test classes)
python -m pytest tests/test_frontend.py -v   # 前端HTML/JS结构 (2 test classes)
```

`conftest.py` 提供会话级 RDN 和 YOLO 模型加载夹具。需要 torch/ultralytics 的测试仅在 conda ican 环境下通过。

---

## 二、algae_guardian — 研究项目

### 启动

```bash
conda activate ican
cd e:/code/codex/code/algae_guardian
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
  - `polarization_sim.py` — Malus定律 + 结构张量模拟
  - `enhancement.py` — 水下颜色校正、CLAHE、暗通道先验去雾
  - `quality.py` — Q 质量评分
  - `eval_charts.py` — PR曲线、F1曲线、训练历史
- `ml/` — 机器学习
  - `reconstructor.py` — RDN残差稠密网络 (4→16→16→4, blocks=12, layers=6)
  - `inference.py` — YOLOv8检测封装
  - `config.py` — 藻种定义(6类)、风险阈值、FOV参数
  - `tracker.py` — 时间窗平均 + 增长速率
  - `preprocessing.py` / `postprocessing.py` — 预处理/后处理
- `backend/` — FastAPI后端
  - `app/models/` — 3表: Device, DetectionRecord, AlertRecord
  - `app/routes/` — detection, devices, dashboard, review (4个路由模块)
  - `app/services/` — detection_service (完整管线编排), risk_assessment (多因子风险评分)
  - SQLite + aiosqlite, WAL模式
- `cloud_training/` — 云服务器训练脚本 (27个.py文件)
  - 数据准备: generate_rdn_data, prepare_h5, prepare_lifewatch, create_split
  - 数据传输: upload_project, deploy_v8l, download_results
  - 训练: train_rdn_cloud, train_yolo_cloud, train_yolo_v8s, train_lifewatch_yolo
  - 处理: batch_process_rdn, simulate_polarization, rdn_reconstruct
  - 监控: monitor.py
- `tests/` — test_pipeline.py, batch_v2_fmpd.py, yolo_v2_infer.py 等

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
- 平台图片: `pic/` 目录 (映射到 `E:/code/codex/pic/`)
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
- `docker-compose.yml` — GPU 透传, 8GB shm, 挂载 `E:/code/codex/datasets` 和 `E:/code/codex/results`
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

`.claude/scheduled_tasks.json` 配置了每小时第 17 分钟执行的监控任务，SSH 连接到云 GPU 服务器检查两组 YOLO 训练状态 (v8l_hsv_95 全量 + v8l_hsv_stable 半数)，报告 epoch/mAP/NaN/GPU 状态。

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
