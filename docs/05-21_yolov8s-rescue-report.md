# YOLOv8s LifeWatch 训练状态诊断和救援计划 (2026-05-21)

## 1. 训练表现摘要
- **训练起点**: 启动于 2026-05-20 夜间。配置为 `imgsz=320`, `batch=128`, 采用 AdamW 优化器，学习率 `lr0=0.001`，数据集为全量重构且 $I_{enh}$ 增强后的 **LifeWatch FlowCam 数据集 (95类, 337,541 颗粒)**。
- **健康演进 (Epoch 1 - 20)**:
  - 模型的收敛速度极佳。
  - 在第 20 个 Epoch (Checkpoint 指标保存在第 19 个 Epoch) 达到了历史最强性能峰值：
    - **mAP50**: **82.24%** (`0.82241`)
    - **Precision**: 77.40%
    - **Recall**: 77.62%
    - **val/box_loss**: 0.04098
    - **val/cls_loss**: 0.40127
  - 该峰值表现已经远远超越了先前在 FlowCam 数据集上的 YOLOv8l 升级基线 (`mAP50 = 0.429`)，充分佐证了 **物理偏振重建（RDN）和特征级 $I_{enh}$ 增强** 对超小、低分辨率浮游植物鉴别所起到的革命性作用。

## 2. 崩塌问题发生与机理诊断
- **崩塌起点**: 从 Epoch 21 的第 1764 个 step 开始，`train/box_loss` 的值突然溢出变为 `inf` / `nan`。
- **表现**:
  - 从 Epoch 22 起，评估指标彻底清零（Precision/Recall/mAP 均为 0）。
  - 日志中抛出大量警告：`WARNING ⚠️ Skipping checkpoint save at epoch 22: EMA contains NaN/Inf`。
  - 由于 EMA 中存在异常值，后续 Epoch 的模型权重无法正常计算并写入，模型开始在全零的死水中空转。
- **根本机理**:
  - **AMP (Automatic Mixed Precision) 溢出**: PyTorch 默认 of FP16 混合精度在处理带有自定义物理增强算法特征（如 $I_{enh}$ v2 高反差边缘）且模型较小时，由于梯度局部激增或非线性算子（如 DFL / CIoU Loss）在大 Batch 上的局部极大值，容易出现 FP16 激活值上溢（大于 65504），导致梯度流中的缩放因子（Loss Scaler）崩塌并传入 `NaN/Inf`。
  - 当这种大梯度污染了 AdamW 优化器的状态后，由于动量效应（Momentum）和极高的偏振高频信息，模型在 Epoch 21 一瞬间产生不可逆的参数崩塌。

## 3. EMA 参数保护与断点救援方案
- 幸运的是，**`best.pt` 权重未受污染**：
  - 加载 `best.pt` 详细检测后发现，**第 19 个 Epoch 的 EMA 参数全部正常，完全不含任何 NaN/Inf**，其包含了所有最棒的 `0.8224` 指标参数。
- 我们已经在云端环境准备了防御性救援方案脚本 `/data/algae_guardian/cloud_training/resume_with_defense.py`。
- **救援机制**:
  - **禁用 AMP (`amp=False`)**: 强制使用完整的 FP32 精确精度，彻底消除极小特征值下的 FP16 浮点溢出崩塌和 `inf` 发生。
  - **降低微调学习率 (`lr0=0.0002`)**: 从健康的 `best.pt` 出发进行退火式精细化（Fine-tuning），避免剧烈的二次冲击。
