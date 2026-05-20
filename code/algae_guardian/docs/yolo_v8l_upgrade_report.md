# YOLOv8l 升级训练报告

## 概述
- **时间**: 2026-05-08
- **模型**: YOLOv8l (43.7M params, 165.4 GFLOPs)
- **数据集**: FMPD 293 张 → RDN 偏振重建 → I_enh → Q 标准化 → 640×640
- **划分**: 训练 234 张 (80%) / 验证 59 张 (20%)，与 baseline 不同不再使用 train=val
- **训练**: 云服务器 RTX 5060 Ti (16GB)
- **训练时长**: 160 epochs / 0.375 小时 (22.5 分钟)

## 与 Baseline 关键差异
| 项目 | Baseline (v8s) | 本次升级 (v8l) |
|------|----------------|----------------|
| 模型参数 | 11.2M | 43.7M |
| 训练/验证划分 | train=val (293张) | 80/20 split (234/59) |
| 验证集 | 全部 293 张 | 59 张 held-out |
| 验证评估 | **虚高** (训练集评估) | **真实泛化性能** |
| 类别权重 | 无 | `pos_weight` 逐类加权 |
| 提前停止 | 283 epochs (best @233) | 160 epochs (best @110) |

## 训练过程
- 前 11 epochs: val/cls_loss 为 inf，模型完全无法预测
- ~epoch 12: 开始收敛，mAP50 突破 0.05
- ~epoch 52: mAP50 突破 0.30
- **最佳 epoch**: 110, mAP50=0.429, mAP50-95=0.197
- Early stopping 触发于 epoch 160 (patience=50)

## 结果

### 全局指标 (best.pt @ epoch 110)
| 指标 | 值 |
|------|-----|
| mAP50 | 0.429 |
| mAP50-95 | 0.197 |
| Precision | 0.466 |
| Recall | 0.496 |

### 各类别 AP
| 类别 | 图像数 | 实例数 | mAP50 | mAP50-95 |
|------|--------|--------|-------|----------|
| Other-phytoplankton | 47 | 176 | 0.276 | 0.129 |
| Non-phytoplankton | 54 | 302 | 0.162 | 0.053 |
| Woronichinia | 19 | 34 | **0.659** | 0.297 |
| Spiroides | 12 | 13 | **0.610** | 0.326 |
| Dinobryon | 32 | 79 | 0.346 | 0.142 |

### 对比 Baseline (注意评估集不同)
| 类别 | Baseline mAP50 (train=val, 293张) | v8l mAP50 (held-out, 59张) |
|------|-------------------------------------|------------------------------|
| Woronichinia | 0.949 | 0.659 |
| Spiroides | 0.988 | 0.610 |
| Dinobryon | 0.779 | 0.346 |
| Other-phytoplankton | 0.682 | 0.276 |
| Non-phytoplankton | 0.468 | 0.162 |
| **Overall** | **0.739** | **0.429** |

> baseline 由于在训练集上验证，mAP50 严重高估。v8l 的 0.429 是对 59 张从未见过的验证集的真实评估。

## 分析

### 类别表现
- **Woronichinia (0.659) / Spiroides (0.610)**: 三类目标藻类中表现最好，特征明显
- **Dinobryon (0.346)**: 中等表现，类内可能存在形态差异
- **Other-phytoplankton (0.276)**: 杂类，包含多种藻类，特征不统一
- **Non-phytoplankton (0.162)**: 最难类别，类内差异大（颗粒/碎屑/浮游动物），Recall 仅 ~16%

### 模型升级效果
1. **更大的模型 (v8s→v8l) 带来的收益有限**: 43.7M 参数对 234 张训练图像来说过参数化，容易过拟合
2. **真实评估很重要**: 使用 held-out 验证集后，mAP50 从虚高的 0.739 降到真实的 0.429
3. **数据量是当前瓶颈**: 234 张训练图像远不足以充分发挥 v8l 的容量

## 改进方向
1. **扩充数据集**: LifeWatch FlowCam 数据 (337k张) 与 FMPD 联合训练
2. **数据增强**: 更强的 Mosaic / MixUp 策略、CutOut、AutoAugment
3. **更小模型**: 回到 YOLOv8m 或 YOLOv8s/s 用 proper split 做真实 benchmark
4. **伪标签**: 用 v8l 对未标注数据生成伪标签，自训练迭代

## 文件位置
- 权重: `data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/best.pt` (87.7MB)
- 结果曲线: `.../results.png`
- 混淆矩阵: `.../confusion_matrix.png`
- 验证预测: `.../val_predict/`
- 训练 CSV: `.../results.csv`
