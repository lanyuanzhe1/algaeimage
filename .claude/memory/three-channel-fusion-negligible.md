---
name: three-channel-fusion-negligible
description: 三通道融合 [S0, I_enh, corrected] vs I_enh×3 在 FMPD 上差异可忽略
metadata:
  type: project
---

2026-06-17 全量 FMPD 293 张测试：三通道融合 vs 单通道 I_enh×3 对比。

结果: 3ch=1054 vs 1ch=1042 检测数 (+1.1%)，平均置信度 0.5317 vs 0.5316（无差异），4/5 类上 3ch 略优但均在误差范围内。

**Why:** I_enh 单通道已将偏振信息充分压缩，加 S0/corrected 通道没有提供模型能有效利用的增量信息。FMPD 仅 293 张训练图、YOLOv8s 容量有限是更根本的瓶颈。

**How to apply:** V2 产线保持 I_enh 单通道 ×3 推理，不需要改。训练/推理 mismatch 在实践上影响为零。能量应投向扩大数据集而非调输入格式。关联: [[ienh-formulas-v1-v2]]
