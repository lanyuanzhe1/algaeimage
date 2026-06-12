---
name: feedback-keep-weights
description: 模型权重即使实验失败也有参考价值，不应清理
metadata:
  type: feedback
---

保留所有权重文件（`*.pt`, `*.pth`），即使来自失败的实验也有参考价值。

**Why:** 用户明确表示"权重这东西不要清，失败的也是有价值的"。失败实验的权重可能包含架构洞察、baseline对比、或后续改进的起点。

**How to apply:** 在清理代码、瘦身目录、或建议删除文件时，永远排除 `weights/` 目录中的 `*.pt` 和 `*.pth` 文件。只清理 `build/`、`dist/`、`__pycache__/` 等构建产物。
