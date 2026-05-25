# 藻影卫士 — 代码目录

## 目录地图

| 目录 | 状态 | 说明 |
|------|------|------|
| `algae_image_v1/` | **🟢 当前产品** | V1.0 桌面工具，一键启动 |
| `algae_guardian/` | 🟡 历史参考 | 原版项目，V1 由此迁移 |
| `Polar_sim_0520/` | 🟡 历史参考 | 结构张量管线实验 (82.24% mAP50) |
| `Polar_sim_0522/` | 🔴 已废弃 | HSV 管线实验 (37.9% mAP50) |
| `SPDRDN/` | 🟡 参考研究 | RDN 网络原始研究仓库 |
| `archive/` | ⚫ 归档 | 云端训练脚本等历史文件 |

## 管线演化

```
SPDRDN (RDN 网络原型)
  ↓
algae_guardian (集成 RDN + 偏振 + YOLO, FMPD 293 张)
  ↓
Polar_sim_0520 (结构张量偏振, LifeWatch 337k, mAP50 82.24%)
  ↓
algae_image_v1 (V1.0 产品, 精简封装, 一键启动)

Polar_sim_0522 (HSV 偏振分支, mAP50 37.9%, 已终止)
```

## 模型权重清单

### 规范副本（V1 产品使用）

| 文件 | 用途 | 训练信息 |
|------|------|----------|
| `algae_image_v1/weights/rdn_polarization.pth` | RDN 偏振重建 | FMPD patches, epoch 97, PSNR **62.46dB**, RTX 5060 Ti |
| `algae_image_v1/weights/best.pt` | YOLOv8s 藻类检测 | LifeWatch 337k 结构张量, YOLOv8s, epoch 19 救援微调, mAP50 **84.7%**, RTX 5060 Ti |

### 历史权重（仅供追溯）

| 文件 | 大小 | 训练背景 |
|------|------|----------|
| `algae_guardian/ml/models/rdn_polarization.pth` | 2.4MB | 与 V1 权重相同，规范副本的原始位置 |
| `algae_guardian/ml/models/yolov8l.pt` | 88MB | YOLOv8l 基础预训练权重 (Ultralytics) |
| `algae_guardian/ml/models/algae_detection.pt` | 6.6MB | 早期 YOLO 检测权重 (FMPD 基线) |
| `algae_guardian/yolov8n.pt` | 6.5MB | YOLOv8n 基础预训练权重 (Ultralytics) |
| `algae_guardian/data/yolo_results/training/weights/best.pt` | - | YOLOv8s FMPD 基线训练 (train=val, mAP50=73.9%) |
| `algae_guardian/data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/best.pt` | - | YOLOv8l FMPD 80/20 划分 (mAP50=42.9%) |
| `Polar_sim_0520/ml/models/rdn_polarization.pth` | 2.4MB | 与规范副本相同 |
| `Polar_sim_0520/yolov8l.pt` | 88MB | YOLOv8l 基础预训练权重 (副本) |
| `Polar_sim_0520/yolo26n.pt` | 5.5MB | YOLO 轻量模型 (实验用) |
| `Polar_sim_0520/output/yolo_training_hsv/v8l_hsv/weights/best.pt` | - | YOLOv8l HSV 训练 (结构张量对比实验) |
| `Polar_sim_0522/yolov8l.pt` | 88MB | YOLOv8l 基础预训练权重 (副本) |
| `Polar_sim_0522/yolo26n.pt` | 5.5MB | YOLO 轻量模型 (副本) |
| `Polar_sim_0522/output/hsv_training_artifacts_20260524/v8l_hsv_stable/weights/best.pt` | - | YOLOv8l HSV stable 训练 (mAP50=37.9%, amp=False, lr0=0.0002) |
| `SPDRDN/code/AOP-branch/checkpoint/epoch_9.pth` | - | RDN AoP 分支早期 checkpoint |
| `SPDRDN/work_agent/cloud_server/AOP-branch/checkpoint/best.pth` | - | RDN AoP 分支云端最佳权重 |
| `SPDRDN/work_agent/cloud_server/DOCP-branch/checkpoint/best.pth` | - | RDN DoCP 分支云端最佳权重 |
| `SPDRDN/work_agent/cloud_server/DOLP-branch/checkpoint/best.pth` | - | RDN DoLP 分支云端最佳权重 |
| `SPDRDN/work_agent/cloud_server/DOP-branch/checkpoint/best.pth` | - | RDN DoP 分支云端最佳权重 |
| `results/yolo_results_20260522/yolo_artifacts/weights/best.pt` | 22MB | LifeWatch YOLOv8s 救援训练 (→ 复制为 V1 weights/best.pt) |

## 启动 V1 产品

```bash
cd algae_image_v1
# 双击 run.bat 或:
conda activate ican
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 访问

| URL | 说明 |
|-----|------|
| `http://localhost:8000/app/` | 前端界面（Dashboard 首页） |
| `http://localhost:8000/docs` | Swagger API 文档 |

## V1 前端界面

蓝青色监控仪表板，6 页面 SPA（`frontend/index.html`），无构建工具，Chart.js 4.4.0 CDN。

### 导航

| 页面 | 状态 | 功能 |
|------|------|------|
| **首页** | 可用 | Dashboard 总览：5 指标卡 + 3 栏布局（统计/检测上传/最近记录+风险摘要+数据闭环） |
| **检测工具** | 可用 | 跳转回首页检测区（核心功能聚集在首页） |
| **历史记录** | 可用 | 分页表格，支持查看详情/删除，Q 质量评分 + 风险等级 |
| **数据统计** | 可用 | Chart.js 饼图（藻类分布）+ 柱状图（风险分布）+ 最近检测列表 |
| **设备管理** | 占位 | 静态展示，后续版本开放 |
| **人工复核** | 占位 | 数据闭环 4 步示意图，后续版本开放 |

### 处理管线可视化

顶部管线 bar 实时展示 5 阶段流程：

```
①偏振暗场采集 → ②Stokes重建 → ③图像增强 → ④YOLO识别计数 → ⑤融合预警
```

检测时管线步骤依次高亮，完成后全部标记绿色 ✓。

### 其他功能

- **导出报告**：点击顶栏按钮，弹窗汇总当前统计数据
- **管线动画**：提交检测时 5 步依次激活（600ms/步），完成后 2s 自动重置
- **自动刷新**：首页每 60s 自动拉取最新统计数据
- **四级风险色**：红（高危）/ 橙（预警）/ 黄（注意）/ 绿（低风险）

## 测试

```bash
cd algae_image_v1
conda activate ican

# 前端结构测试（30 用例）
python -m pytest tests/test_frontend.py -v

# 核心管线测试（14 用例，需要模型权重）
python -m pytest tests/test_pipeline.py -v
```

## 关键文档

- 产品设计规格: `algae_image_v1/docs/V1_design_spec.md`
- **前端改版设计**: `../docs/superpowers/specs/2026-05-25-v1-frontend-redesign-design.md`
- **前端改版计划**: `../docs/superpowers/plans/2026-05-25-v1-frontend-redesign-plan.md`
- 实施计划: `algae_image_v1/docs/superpowers/plans/2026-05-24-V1-implementation.md`
- 全链路训练总结: `../docs/algae_polarization_training_summary_20260523.md`
- 结构张量管线设计: `Polar_sim_0520/docs/pipeline_design.md`
- HSV 管线设计: `Polar_sim_0522/docs/design.md`
- 救援训练报告: `../docs/yolov8s_rescue_report_20260521.md`
