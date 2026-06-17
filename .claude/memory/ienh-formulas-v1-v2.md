---
name: ienh-formulas-v1-v2
description: 代码库中存在两条不同的 I_enh 公式，训练用 v1、V2 推理用 v2
metadata:
  type: project
---

两条 I_enh 公式共存于代码库：

**v1** (`algae_guardian/image_processing/polarization.py → polarization_enhancement`):
```
I_enh = Norm(S0_norm + 0.3·S0_norm + 0.2·AoP_norm + 0.4·DoLP_norm)
```
加法式，各分量独立归一化后相加。YOLO 训练数据的三通道融合 G 通道使用此公式。

**v2** (`algae_image_v2/core_engine/enhancement.py → enhance()` + `polarization.py → polarization_enhancement_v2`):
```
I_enh = Norm( S0_norm × (1.0 + 0.6 - 0.35·DoLP + 0.25 × |sin(2·AoP)| × DoLP) )
```
减法式（去散射），乘积后单次归一化。V2 产线当前使用此公式。

**Why:** 训练/推理公式不一致是潜在风险，但全量测试表明影响可忽略。

**How to apply:** 讨论 I_enh 时需指定是哪个版本。v2 更物理（DoLP 减法 = 去散射），v1 是历史遗留。[[three-channel-fusion-negligible]]
