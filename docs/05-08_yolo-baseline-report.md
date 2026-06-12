# YOLOv8s Baseline 训练报告

## 概述

在 FMPD 数据集（293 张显微藻类图像）上训练 YOLOv8s 作为基线模型。数据先经过 RDN 偏振重建 → I_enh 增强 → Quality 标准化的完整预处理管线。

## 训练参数

| 参数 | 值 |
|------|-----|
| 模型 | YOLOv8s (11.2M params) |
| 输入尺寸 | 640×640 |
| 优化器 | AdamW |
| 初始学习率 | 0.001 |
| Batch | 32 |
| Epochs | 283（早停触发） |
| 最佳 Epoch | 233 |
| 设备 | NVIDIA GeForce RTX 5060 Ti (16GB) |
| 训练耗时 | ~21 分钟 |

### 数据增强

mosaic=1.0, mixup=0.1, hsv_h=0.015, hsv_s=0.7, hsv_v=0.4, degrees=10, translate=0.1, scale=0.5, fliplr=0.5

## 数据集

**FMPD (Freshwater Microscopy Phytoplankton Dataset)**

来源: 西班牙 Doniños 湖，10× 明场显微成像，2080×1540 TIF。

| 类别 | 说明 | 实例数 |
|------|------|--------|
| Non-phytoplankton | 非浮游植物（颗粒、碎屑、浮游动物等干扰物） | 1723 |
| Other-phytoplankton | 其他浮游植物（除三种特定藻类外的杂类） | 794 |
| Dinobryon | 锥囊藻（无害，可单细胞或群体出现） | 354 |
| Woronichinia | 沃氏藻（产毒蓝藻） | 233 |
| Spiroides | 螺旋藻（产毒蓝藻） | 58 |

**共计**: 293 张图像，3162 个标注实例，5 类。

## 训练结果

### 全局指标

| 指标 | 最佳值 | 说明 |
|------|--------|------|
| mAP50 | **0.739** | IoU=0.5 时的平均精度 |
| mAP50-95 | **0.472** | IoU 0.5~0.95 的平均精度 |
| Precision | 0.854 | 精确率 |
| Recall | 0.706 | 召回率 |
| 推理速度 | 6.6 ms/张 | RTX 5060 Ti |

### 各类别性能

| 类别 | P | R | mAP50 | mAP50-95 | 分析 |
|------|---|---|-------|----------|------|
| Other-phytoplankton | 0.711 | 0.642 | 0.682 | 0.463 | 杂类，类内差异大 |
| Non-phytoplankton | 0.729 | **0.343** | **0.468** | **0.274** | 干扰物，形态极其多样 |
| Woronichinia | 0.780 | 0.996 | 0.949 | 0.721 | 形态特征明显 |
| Spiroides | 0.845 | 1.000 | **0.988** | **0.822** | 螺旋结构易识别 |
| Dinobryon | 0.693 | 0.819 | 0.779 | 0.519 | 群体/单体形态多变 |

### 训练曲线

训练曲线见 `training/results.png`，包含 loss、P、R、mAP 随 epoch 的变化。

## 分析

### 性能解读

1. **Spiroides (98.8%) 和 Woronichinia (94.9%)** 表现优秀 — 这两种藻类具有鲜明的螺旋/群体形态特征，易于识别。
2. **Dinobryon (77.9%)** 表现中等 — 可单细胞或群体出现，形态多变。
3. **Other-phytoplankton (68.2%)** 偏低 — 作为"杂类"包含多种不同藻种，类内差异大。
4. **Non-phytoplankton (46.8%)** 最差 — 这不是一个语义类别，而是"一切非藻类物体"的集合（气泡、纤维、浮游动物、尘埃等），类内差异极大，recall 仅 34%。

### 局限性

- 仅 293 张训练图像，数据量偏少
- Non-phytoplankton 和 Other-phytoplankton 本质上是"垃圾抽屉"类，定义过于宽泛
- 单一时段单一地点的采样，泛化性未知

## 结论

作为 baseline，YOLOv8s 在 293 张图上达到 73.9% mAP50。**三种目标藻类（Woronichinia/Spiroides/Dinobryon）的 mAP50 达 90.5%**。性能瓶颈在 Non-phytoplankton 类别，改善方向包括：

1. 重新定义 Non-phytoplankton 的标注粒度
2. 扩充数据集（如 LifeWatch FlowCam 337k 张）
3. 尝试 YOLOv8l 或 YOLOv11 等更大模型

## 输出文件位置

- 最佳权重: `data/yolo_results/training/weights/best.pt`
- 预测结果图: `data/yolo_results/predictions/`（293 张带检测框的 JPG）
- 训练曲线: `data/yolo_results/training/results.png`
- 详细日志: `data/yolo_results/training/train.log`
