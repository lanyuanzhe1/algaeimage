---
name: project-context
description: 藻影卫士偏振显微监测 — 当前状态与目标，2026-06-13 更新
metadata:
  type: project
---

## 项目定位

藻类显微图像偏振检测的研究到产品管线。

| 目录 | 状态 | 说明 |
|------|------|------|
| `code/algae_image_v2/` | **当前产品主线** | V2.0，5类FMPD，HSV偏振，样机演示阶段 |
| `code/algae_image_v1/` | 稳定备份 | V1.0，95类LifeWatch，结构张量+RDN，论文答辩版 |
| `code/algae_guardian/` | 研究参考 | 训练/评估/实验 |
| `code/Polar_sim_0520/` | 算法来源 | 结构张量管线，mAP50 84.7% |
| `code/Polar_sim_0522/` | 已废弃 | HSV 管线实验，含 Docker 训练环境 |
| `code/RDN_HSV_0526/` | 实验对照 | HSV+RDN 对照实验，为V2跳过RDN提供实验依据 |

**当前分支**: `HSV`。已全部 git 提交并推送 origin。

## 近期进展

- V2 exe 封装已完成（PyInstaller onedir，dist-release/）
- Vue3 前端已迁移并丰富化（6 页面 SPA）
- 阿里云 ECS 部署完成：前端 nginx + 后端 FastAPI systemd
- **样机演示全链路贯通**: 海康 MV-CA013-20GC SDK 直连 → 一键启动 → 双栏实时展示（原始+YOLO标注）
- Camera SD集成进 backend 进程（CameraController），前端独立路由 /detect/live
- 跨页面采集保持、历史页自动轮询、DB 实时写入
- **性能优化**: run_ndarray() 跳过文件I/O、JPEG替代PNG、批量DB写入
- **时间戳修复**: UTC+8（SQLite CURRENT_TIMESTAMP → datetime('now','+8 hours')）
- 有效处理速度 ~1.5-1.8fps（瓶颈在 YOLOv8l GPU 推理+HSV偏振）
- 后续瓶颈：采集更多数据扩充 FMPD（当前仅293张）

## 环境

- 本地: Windows 11, conda `ican` (Python 3.11, A:\Anaconda_envs\envs\ican)
- 本地 GPU: RTX 4050 Laptop 6GB
- 云 GPU: RTX 5060 Ti 16GB (训练用)
- 模型后端: DeepSeek v4-pro[1m]
