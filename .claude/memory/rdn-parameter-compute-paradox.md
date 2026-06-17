---
name: rdn-parameter-compute-paradox
description: RDN 0.61M 参数 → 865 GMACs，参数少≠计算少
metadata:
  type: project
---

RDN 参数量 612,356 ≈ 0.61M（CLAUDE.md 记载正确），但计算量 865 GMACs @ 1024px = YOLOv8s 的 30.5 倍。

根因: Dense Connection 导致通道膨胀——每个 RDB 内 6 个 DenseLayer 的输入通道从 16 逐层增长到 96。最后一层 Conv2d(96, 16, 3) 单层贡献 13,840 MAC/px。

12 RDBs × 6 dense layers = 72 个全 3×3 卷积，无瓶颈、无下采样。

**Benchmark** (GPU):
- 2080×1540: 8.69s/forward
- 1024×1383: 2.32s/forward
- 512×691: 0.56s/forward

**Why:** 避免误认为"参数少=跑得快"。RDN 是轻量参数、重量计算的典型——每个参数被复用的次数极多。

**How to apply:** PIPELINE_MAX_WIDTH=1024 是必需的。讨论加速时重点不在压缩参数而在减少计算（剪枝 RDB 数量、引入分组卷积、或考虑跳过 RDN）。
