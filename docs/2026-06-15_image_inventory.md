# 项目图片资产清单 (Image Inventory)

> 生成日期: 2026-06-15 | 分支: `rdn-analysis`
> 覆盖范围: `code/` 全部子项目 + `pic/` + `docs/reference_images/`
> 约 **95,819** 张图片文件

---

## 一、总览

| # | 位置 | 图片数量 | 主要格式 | 管线阶段 |
|---|------|----------|----------|----------|
| 1 | `pic/` | 32 | jpg/png/svg/webp | 演示/文档素材（非管线产出） |
| 2 | `code/algae_image_v2/` | 2,219 | jpg(上传) + png/jpg(结果) | Web 应用：用户上传 → YOLO 检测 |
| 3 | `code/algae_image_v1/` | 360 | jpg(上传) + png(结果) | Web 应用 v1 |
| 4 | `code/algae_guardian/` | ~90,309 | tif+jpg+png | **全管线**: TIFF→偏振→RDN→YOLO |
| 5 | `code/Polar_sim_0520/output/` | 1,831 | jpg/png + .npz | **293样本全管线批量** |
| 6 | `code/Polar_sim_0522/` | 1,007 | jpg | 500样本 Flowcam 批次 |
| 7 | `code/SPDRDN/` | 60 | png | SPDRDN 偏振去噪参数图 |
| 8 | `code/RDN_HSV_0526/` | 0 | — | 训练工作区（无可视化输出） |
| 9 | `docs/reference_images/` | 7 | jpg | 网上下载的参考明场图 |

---

## 二、管线数据流

```
[原始 TIFF 显微图]              [FlowCam JPG]               [用户上传 JPG/PNG]
       │                              │                            │
       ▼                              ▼                            ▼
 偏振模拟 (.npz)               偏振模拟 (.npz)              直接 YOLO 检测
 I0/I45/I90/I135               I0/I45/I90/I135
       │                              │
       ▼                              ▼
 RDN 去噪重建                  RDN 去噪重建
 S0/S1/S2/DoLP/AoP            S0/DoLP/AoP/I_enh
       │                              │
       ▼                              ▼
 I_enh v2 增强                I_enh v2 增强
       │                              │
       ▼                              ▼
 YOLOv8 检测                  YOLOv8 检测
 (边界框标注)                  (边界框标注)
       │                              │
       ▼                              ▼
 最终输出                      最终输出
 (hsv_final/, struct_final/)   (preview/)
```

---

## 三、逐目录详析

### 3.1 `pic/` — 演示与文档素材（32 张）

> 人工整理的演示图片，非管线自动产出。用于文档、PPT、README。

#### 原始 vs 增强对照（★ 配图首选）

| 文件 | 分辨率 | 说明 |
|------|--------|------|
| `raw_microscope.jpg` | 2080×1540 | 偏振单通道原始图（灰度）— 可作「传统明场」对照组 |
| `enhanced_microscope.jpg` | 2080×1540 | I_enh v2 增强后 |
| `detect_microscope.jpg` | — | YOLO 检测标注结果 |

#### 偏振可视化

| 文件 | 说明 |
|------|------|
| `stokes_preview.jpg` | Stokes 参数预览 (S0/S1/S2) |
| `dolp_preview.jpg` | 线偏振度 DoLP 伪彩图 |
| `aop_preview.jpg` | 偏振角 AoP 伪彩图 |

#### YOLO 相关

| 文件 | 说明 |
|------|------|
| `YOLO输入输出.png` | YOLO 输入/输出对比 |
| `YOLO输出.png` / `YOLO输出.svg` | YOLO 检测输出 |
| `YOLO流程.png` | YOLO 处理流程 |
| `YOLOv8结构图.jpg` | YOLOv8 网络架构图 |
| `YOLO测试集输出.svg` | 测试集检测结果 |

#### 网络架构图

| 文件 | 说明 |
|------|------|
| `RDN网络.png` | RDN 残差稠密网络架构 |
| `三通道原始图RDN输入.png` | RDN 输入通道示意 |

#### 评估与业务

| 文件 | 说明 |
|------|------|
| `eval_summary.png` / `eval_summary.svg` | 评估总结 |
| `4.2商业模式.png` | 商业模式图 |
| `实物图.png` | 设备实物照片 |
| `藻影卫士平台预警界面原型.png` | 平台 UI 原型 |
| `藻华拼图.png` | 藻华拼图 |

#### 实景藻类参考

| 文件 | 说明 |
|------|------|
| `水藻1.jpg` / `水藻2.png` | 水藻实拍 |
| `显微藻华.jpg` | 显微藻华 |
| `核电站藻华图.jpg` | 核电站藻华案例 |
| `近海水藻.jpg` | 近海水藻 |
| `藻华.webp` | 藻华现象 |

#### `yolo_intermediate/` — 训练过程图（6 张）

| 文件 | 说明 |
|------|------|
| `confusion_matrix_normalized.png` | 归一化混淆矩阵 |
| `results.png` | 训练结果总览 |
| `training_curves.png` | 训练曲线 |
| `train_batch0~2.jpg` | 训练批次样本 |

---

### 3.2 `code/algae_image_v2/` — V2.0 Web 应用（2,219 张）

#### `backend/data/uploads/` — 用户上传原始图（1,109 张）

- **内容**: 用户通过 Web 界面上传的 RGB 显微图像
- **格式**: jpg (1,084) + png (24) + tif (1)
- **命名**: UUID 格式，如 `0005f1302d4d40e2a9fca4874cc941c4.jpg`
- **管线阶段**: 原始输入

#### `backend/data/results/` — YOLO 检测结果（1,110 张）

| 子目录 | 数量 | 格式 | 说明 |
|--------|------|------|------|
| `results/` (根) | 551 | png | UUID 对应的 YOLO 检测标注图 |
| `results/live/` | 559 | jpg | 实时相机采集原始帧，`raw_000001.jpg` ~ `raw_000559.jpg` |

---

### 3.3 `code/algae_image_v1/` — V1.0 Web 应用（360 张）

| 目录 | 数量 | 格式 | 说明 |
|------|------|------|------|
| `backend/data/uploads/` | 180 | jpg(174) + tif(6) | 用户上传原始图 |
| `backend/data/results/` | 180 | png | YOLO 检测结果（UUID 一一对应） |

---

### 3.4 `code/algae_guardian/` — 研究项目全管线（~90,309 张）

#### 3.4.1 原始显微图 — TIFF

| 路径 | 数量 | 格式 |
|------|------|------|
| `data/download/extracted/dataset/dataset/` | **586** | .tif |

> FMPD 数据集原始 FlowCam 显微图像，命名格式 `SNAP-003217-0030.tif`

#### 3.4.2 偏振模拟输出

| 路径 | 数量 | 内容 |
|------|------|------|
| `data/download/extracted/dataset/polarized/preview/` | 879 | Stokes 可视化: `*_stokes.jpg`, `*_dolp.jpg`, `*_aop.jpg` |
| `data/download/extracted/dataset/polarized/enhanced_preview/` | 534 | RDN-I_enh 增强预览 |

#### 3.4.3 RDN 去噪输出（293 样本 × 9 通道）

| 子目录 | 数量 | 格式 | 内容 |
|--------|------|------|------|
| `data/rdn_output_v2/s0/` | 293 | png | 去噪 S0（总光强，等同明场图） |
| `data/rdn_output_v2/s1/` | 293 | png | 去噪 S1（0°/90° 差异） |
| `data/rdn_output_v2/s2/` | 293 | png | 去噪 S2（45°/135° 差异） |
| `data/rdn_output_v2/dolp/` | 293 | png | 线偏振度 DoLP |
| `data/rdn_output_v2/aop/` | 293 | png | 偏振角 AoP |
| `data/rdn_output_v2/ienh/` | 293 | png | **I_enh v2 增强** |
| `data/rdn_output_v2/corrected/` | 293 | png | 色彩校正输出 |
| `data/rdn_output_v2/images/` | 293 | jpg | JPEG 显示版 |
| `data/rdn_output_v2/preview/` | 293 | jpg | Stokes 综合预览 |

#### 3.4.4 YOLO 检测结果

| 路径 | 数量 | 内容 |
|------|------|------|
| `data/yolo_results/predictions/` | 293 | YOLO 检测标注图 |

#### 3.4.5 YOLO 训练评估指标

| 路径 | 关键文件 |
|------|----------|
| `data/fmpd_rdn_output/yolo_results/v8l_upgrade/` | confusion_matrix.png, BoxF1_curve.png, BoxPR_curve.png, results.png 等 |

#### 3.4.6 FlowCam 训练数据集

| 路径 | 数量 | 说明 |
|------|------|------|
| `data/Flowcam_images_training_split_metadata/.../Flowcam_images_training/` | **83,254** | 24 个分类的 FlowCam 训练图像 |

> 主要类别：Chaetoceros(8,800), Artefact(8,800), Centric_Diatom(8,799), Bacillariophyceae(8,798) 等

---

### 3.5 `code/Polar_sim_0520/output/` — 293 样本全管线批量（1,831 张）

> **这是最完整的管线中间产物目录**，覆盖从偏振模拟到 YOLO 检测的全流程。

#### 管线阶段映射

| 子目录 | 数量 | 格式 | 管线阶段 |
|--------|------|------|----------|
| `polarization_hsv/` | 293 | .npz | 偏振模拟数值结果 (I0/I45/I90/I135) |
| `polarization_struct/` | 3 | .npz | 结构张量法偏振模拟 |
| `preview_hsv/` | 35 | jpg | Stokes 预览 (I0/I45/I135/DoLP/grid) |
| `hsv_preview_293/` | 293 | jpg | 全量 293 样本网格预览 |
| `rdn_output_hsv/` | 293 | jpg | RDN 去噪 HSV 图像 |
| `rdn_output_struct/` | 3 | jpg | RDN 去噪结构张量图像 |
| `yolo_input_hsv/` | 293 | jpg | YOLO 输入 (I_enh 增强后) |
| `yolo_input_struct/` | 3 | jpg | YOLO 输入 (结构张量) |
| `yolo_results_hsv/` | 293 | jpg | **YOLO 检测结果 (HSV 法)** |
| `yolo_results_struct/` | 293 | jpg | **YOLO 检测结果 (结构张量法)** |
| `hsv_final/` | 5 | jpg | 精选最终输出 |
| `struct_final/` | 5 | jpg | 精选最终输出 |
| `comparisons/` | 5 | jpg | **并排对比图** (★ 配图首选) |

#### ★ 精选对比图 (`comparisons/`)

| 文件 | 说明 |
|------|------|
| `SNAP-003217-0030.jpg` | 样本对比: 原始→HSV→Struct→YOLO |
| `SNAP-005459-0015.jpg` | 同上 |
| `SNAP-011621-0021.jpg` | 同上 |
| `SNAP-011632-0022.jpg` | 同上 |
| `SNAP-011703-0023.jpg` | 同上 |

#### YOLO 训练工作区 (`yolo_training_hsv/`)

| 路径 | 内容 |
|------|------|
| `train/images/` | 234 训练集图像 |
| `val/images/` | 59 验证集图像 |
| `v8l_hsv/` | 训练诊断图 (confusion matrix, F1/PR curves, results.png) |

---

### 3.6 `code/Polar_sim_0522/` — 500 样本 FlowCam 批次（1,007 张）

| 路径 | 数量 | 格式 | 说明 |
|------|------|------|------|
| `data/final_samples_500/` | 500 | jpg | FlowCam 输入 |
| `output/preview_2026-05-22/` | 500 | jpg | 管线输出预览 |
| `output/hsv_training_artifacts_20260524/v8l_hsv_stable/` | 7 | png/pt/csv | YOLOv8l 训练指标 |

---

### 3.7 `code/SPDRDN/` — SPDRDN 偏振去噪参数图（60 张）

> 4 个训练分支 × 3 个测试图 × 5 个输出通道 = 60 张

| 分支 | 输出内容 |
|------|----------|
| `AOP-branch/` | S0 / DoLP / AoP / DoCP 去噪图 |
| `DOCP-branch/` | 同上 |
| `DOLP-branch/` | 同上 |
| `DOP-branch/` | 同上 |

> 每个分支在 `result/depart/` 下含 `test_0_s0.png` ~ `test_2_docp.png` 共 15 张

---

### 3.8 `code/RDN_HSV_0526/` — RDN 训练实验

> **无渲染输出图像。**仅含 .mat 数值数据、checkpoint .pth 权重、训练脚本。

---

### 3.9 `docs/reference_images/` — 网上公开参考明场图（7 张）

| 文件 | 分辨率 | 类型 | 来源 |
|------|--------|------|------|
| `Microscopic_algae.jpg` | 4032×3024 | 混合藻类 RGB | Wikimedia CC |
| `Volvox_aureus.jpg` | 2700×2700 | 团藻 CMYK | Wikimedia CC |
| `Diatom_brightfield.jpg` | 2275×1523 | 硅藻 RGB | Wikimedia CC |
| `diatoms_noaa_brightfield.jpg` | 1796×1180 | 硅藻 RGB | NOAA Public Domain |
| `Ceratium_hirundinella.jpg` | 1010×2020 | 角藻 灰度 | Wikimedia CC |
| `noaa_marine_algae_gulf.jpg` | 958×634 | 海藻 RGB | NOAA Public Domain |
| *(模糊图待 deep-research 补充)* | | | |

---

## 四、配图建议 — 对照用关键图片位置

### 传统明场（"普通显微"）

| 用途 | 图片来源 |
|------|----------|
| 明场硅藻（边界模糊） | `docs/reference_images/Diatom_brightfield.jpg` |
| 明场团藻（透明感强） | `docs/reference_images/Volvox_aureus.jpg` |
| 原始偏振单通道 (灰度、低对比) | `pic/raw_microscope.jpg` |
| RDN 去噪 S0（相当于明场） | `algae_guardian/data/rdn_output_v2/s0/SNAP-*-0030.png` |

### 偏振成像（"偏振响应维度"）

| 用途 | 图片来源 |
|------|----------|
| DoLP 伪彩图 | `pic/dolp_preview.jpg` |
| AoP 伪彩图 | `pic/aop_preview.jpg` |
| Stokes 参数综合 | `pic/stokes_preview.jpg` |
| 偏振模拟四通道 (I0/I45/I90/I135) | `Polar_sim_0520/output/preview_hsv/SNAP-*_grid.jpg` |
| RDN 去噪 DoLP | `algae_guardian/data/rdn_output_v2/dolp/SNAP-*-0030.png` |

### 增强 + 检测结果

| 用途 | 图片来源 |
|------|----------|
| I_enh v2 增强 | `pic/enhanced_microscope.jpg` |
| YOLO 检测标注 | `pic/detect_microscope.jpg` |
| 全管线并排对比 | `Polar_sim_0520/output/comparisons/SNAP-*-0030.jpg` |
| I_enh (RDN 后) | `algae_guardian/data/rdn_output_v2/ienh/SNAP-*-0030.png` |

---

## 五、文件格式统计

| 格式 | 约计数 | 主要分布 |
|------|--------|----------|
| `.jpg` | ~88,000 | FlowCam 训练集 + Web 上传 + 管线输出 |
| `.png` | ~5,000 | RDN 输出 + YOLO 结果 + 演示素材 |
| `.tif` | ~600 | FMPD 原始显微图 |
| `.npz` | ~300 | 偏振模拟数值结果 |
| `.svg` | 3 | 演示用矢量图 |
| `.webp` | 1 | 藻华图 |

---

## 六、注意事项

- **模型权重不在 git 中**: `*.pt`, `*.pth` 已被 `.gitignore` 排除
- **TIFF 原始图不在 git 中**: `*.tif` 被 LFS 追踪但未提交
- **`.npz` 偏振数据不在 git 中**: 体积大（~50MB/文件）
- **`dist/` 前端构建产物**: 已在 `.gitignore` 中，需 `git add -f` 提交
- **SPDRDN 是嵌套独立仓库**: 不在父仓库 git 管理中
