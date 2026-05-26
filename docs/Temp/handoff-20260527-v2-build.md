# Handoff: algae_image_v2 搭建与会话上下文

**日期**: 2026-05-27  
**分支**: `HSV` (clean)  
**主题**: V2 产品搭建、HSV 管线实验、RDN 训练、前端优化

## 当前状态

`code/algae_image_v2/` 已搭建完成并运行在 `http://localhost:8000`。

### V2 管线

```
RGB 原图 → HSV 偏振模拟 → I_enh v2 增强 → YOLOv8l 检测 → 5 类输出
```

- **跳过了 RDN**（实验证明 HSV 无需 RDN，加 RDN 反而 mAP50 从 0.354 降到 0.330）
- YOLO 默认模型: `weights/best_v8l.pt`（mAP50 0.429, 80/20 划分）
- 备选模型: `weights/best_v8s.pt`（mAP50 0.739, train=val 虚高）
- API 通过 `?model=v8s` 切换

### 核心改动（相对 v1）

| 文件 | 改动 |
|------|------|
| `core_engine/polarization_sim.py` | 结构张量 → HSV（H→AoP, S→DoLP, V→S0） |
| `core_engine/config.py` | 95类 LifeWatch → FMPD 5类 + 中文名 + 模型选择字典 |
| `core_engine/inference.py` | 新增 `load_yolo_by_key()` / `get_available_models()` |
| `backend/app/main.py` | 去掉 RDN 加载，用 `PipelineRunner.create()` 工厂 |
| `backend/app/services/pipeline.py` | 跳过 RDN 步骤，检测框加粗3倍/标签4倍 |
| `backend/app/routes/detection.py` | 新增 `/api/v1/preview`（TIF→PNG 预览）+ `model` 参数 |
| `backend/app/schemas.py` | `DetectionItem` 新增 `class_name_zh` |
| `frontend/css/style.css` | 标题字号翻倍（40-56px）、导航/面板/管线步骤放大 |
| `frontend/js/detection.js` | TIF 预览走服务端、检测列表显示中文藻种名 |

### 5 类藻种

Other-phytoplankton→其他浮游植物, Non-phytoplankton→非浮游植物(杂质), Woronichinia→沃氏藻(高危), Spiroides→螺旋藻(中危), Dinobryon→锥囊藻(中危)

### 已知限制

- **检测框标签是英文**：OpenCV Hershey 字体不支持中文，图片上显示英文类名，网页列表显示中文
- YOLOv8l mAP50 仅 0.429（FMPD 293 张小样本限制）
- 前端设备管理/人工复核页面仍为占位

## RDN_HSV_0526 实验记录

`code/RDN_HSV_0526/` 包含完整实验：

| 实验 | 管线 | mAP50 |
|------|------|-------|
| 参考 | 结构张量+RDN+YOLOv8l | 0.429 |
| 2 | HSV+新RDN(22dB)+YOLOv8l | 0.330 |
| 3 | HSV无RDN+YOLOv8l | 0.354 |
| 3b | 结构张量无RDN+YOLOv8l | 0.069 |

详见 `code/RDN_HSV_0526/README.md`

## 启动方式

```bash
conda activate ican
cd e:/code/codex/code/algae_image_v2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# 或双击 run.bat
```

## 当前未完成

- 前端管线步骤描述（pipeline bar）仍是 V1 旧文字，未更新为 HSV 管线步骤
- 前端副标题仍是旧文字
- Dinobryon / Non-phytoplankton 检测率低，可能需要补充训练数据
- 用户提到检测结果模块应显示检出藻种中文名和数量——前端检测列表已用中文，但可能需要进一步突出显示

## 相关资源

- V2 用户指南: `code/algae_image_v2/README.md`
- RDN 实验文档: `code/RDN_HSV_0526/README.md`
- 训练总结: `docs/algae_polarization_training_summary_20260523.md`
- V1 参考: `code/algae_image_v1/`
- CLAUDE.md: 项目全景（含数据集路径、权重清单）

## Suggested Skills

- `superpowers:brainstorming` — 如需继续优化管线或设计新功能
- `superpowers:verification-before-completion` — 修改代码后验证
- `feature-dev:feature-dev` — 较大的功能开发（如人工复核模块）
- `frontend-design:frontend-design` — 前端 UI 改进
