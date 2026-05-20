# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 运行命令

```bash
# 激活环境
conda activate ican

# 启动后端 (FastAPI, 端口8000)
cd e:/code/codex/code/algae_guardian
python run.py                # 初始化数据库+加载模型
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 单独启动 (跳过初始化)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 运行测试
python -m pytest tests/test_pipeline.py -v
```

访问: API文档 `http://localhost:8000/docs`, 监控面板 `http://localhost:8000/static/index.html`

## 项目架构

### 处理管线 (不可变更顺序)
```
RGB原图 → 偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh增强 → YOLO检测 → 融合预警
```

### 模块结构
- `image_processing/` — 偏振处理、增强、质量评估
  - `polarization_sim.py` — Malus定律 + 结构张量模拟四通道偏振
  - `enhancement.py` — I_enh公式增强: `S0 + λ1·S0 + λ2·AoP + λ3·DoLP`
  - `quality.py` — Q质量评分
- `ml/` — 机器学习
  - `reconstructor.py` — RDN残差稠密网络(4→16→16→4, blocks=12, layers=6)
  - `inference.py` — YOLOv8检测封装
  - `config.py` — 藻种定义(6类)、风险阈值、FOV参数
  - `tracker.py` — 时间窗平均 + 增长速率
- `backend/` — FastAPI后端 (routes: detection, devices, dashboard)
  - SQLite + aiosqlite, 图像上传/检测/设备管理/仪表板 API
  - `static/results/` 和 `static/uploads/` 在启动时自动创建
- `cloud_training/` — 云服务器训练脚本
- `tests/` — test_pipeline.py (7项测试), generate_samples.py (独立脚本)

### 模型权重
- `ml/models/rdn_polarization.pth` — RDN偏振重建 (PSNR 62.46dB @ epoch 97)
- `ml/models/algae_detection.pt` → `yolov8n.pt` — YOLOv8n-P v0.9
- `ml/models/yolov8l.pt` → `data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/best.pt` — YOLOv8l升级 (mAP50=0.429)

## 关键数据目录

### FMPD 数据集 (293张FlowCam真实显微图像)
- **原始TIFF**: `data/fmpd_download/extracted/dataset/dataset/*.tif`
- **偏振模拟结果** (.npz): `data/fmpd_download/extracted/dataset/polarized/polarization/`
- **偏振预览图** (Stokes/AoP/DoLP): `data/fmpd_download/extracted/dataset/polarized/preview/`
- **增强预览图**: `data/fmpd_download/extracted/dataset/polarized/enhanced_preview/`
- **RDN输出** (I_enh): `data/fmpd_rdn_output/images/`
- **YOLO预测结果** (已画检测框): `data/yolo_results/predictions/`

### 平台静态资源
- 平台页面: `algae_guardian_platform.html` (根目录)
- 平台图片: `pic/` 目录 (raw_microscope.jpg, enhanced_microscope.jpg, detect_microscope.jpg, stokes/aop/dolp_preview.jpg)
- 技术文档: `项目文书/藻影知微_0508.md`

## 关键设计决策

- **I135 不是 I0/I90 平均**: 4个偏振通道全部用同一 Malus 物理模型独立计算，保证 S2 = I45 - I135 有物理意义
- **DoFP偏振相机**: 采集 I0/I45/I90 三个方向，S0 = I0+I90, S1 = I0-I90, S2 = I45-I135
- **训练数据增强**: 藻类区域(green_ratio>0.33)额外增加30%偏振差异
- **数据量是当前瓶颈**: YOLOv8l mAP50=0.429 < v8s mAP50=0.739(虚高), 234训练张不足以支撑大模型

## YOLO训练状态
- **v8s Baseline**: mAP50=0.739 (train=val评估, 虚高), best @epoch 233
- **v8l Upgrade**: 80/20分, mAP50=0.429, mAP50-95=0.197, best @epoch 110
- 最佳类别: Woronichinia 0.659, Spiroides 0.610; 最差: Non-phytoplankton 0.162

## 前端与数据闭环

### 访问地址 (后端启动后)
- 新平台前端: `http://localhost:8000/app/`
- 旧监测面板: `http://localhost:8000/static/index.html`
- API文档: `http://localhost:8000/docs`

### 数据闭环流程 (真实持久化)
- `frontend/index.html` → 访问 `http://localhost:8000/app/`（由FastAPI挂载）
- 点击"人工复核" → POST `/api/v1/review/submit` → 保存到 `backend/data/reviewed/{review_id}/`
  - 每个复核记录保存: `metadata.json`(站点、物种、风险等) + 当前显微图像副本
- 点击"加入训练集" → POST `/api/v1/review/approve/{id}` → 复制到 `backend/data/training_pool/{review_id}/`
- 图片通过 `/pic/` 挂载提供 (映射到 `e:/code/codex/pic/`)

### 关键路由
- `backend/app/routes/review.py` — 复核/训练数据持久化API
- `/static/` — 旧静态文件
- `/app/` — 新前端
- `/pic/` — 平台图片
