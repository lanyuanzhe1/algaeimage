---
name: lifewatch-84percent-is-classification
description: 84.7% mAP50 实质是分类准确率而非目标检测精度
metadata:
  type: project
---

LifeWatch YOLOv8s 的 84.7% mAP50 是在 13,037 张验证集上、epoch ~25 救援微调后取得的。

**关键 caveat**: LifeWatch 每张图只有一个物体，标注框为全图 bbox (`0.5 0.5 1.0 1.0`)。定位任务 trivial——任何覆盖大部分画幅的预测框 IoU > 0.5。mAP50 实际度量的是 **95 类分类准确率**，不是真正的目标检测。

FMPD 才是真正的检测任务（每图 ~10.8 个目标，大小位置各异），mAP50 42-74%。

**Why:** 避免混淆这两个数字的含义。84.7% 在竞赛文书里可以写，但答辩时要能解释等价于 classification accuracy。

**How to apply:** 引用 LifeWatch 结果时注明"全图单目标标注，等价于分类精度"。对比 FMPD 结果时强调 FMPD 才是真正的多目标检测。
