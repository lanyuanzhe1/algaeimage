---
name: reference-external
description: 外部资源指针 — 代码仓库、云服务器、竞赛文书、阿里云部署、关键文档位置
metadata:
  type: reference
---

## 代码仓库

- GitHub: `https://github.com/lanyuanzhe1/algaeimage.git`
- 知识笔记: `E:\code\learn\` (claude-code-knowledge.md, 网络学习.md)

## 云 GPU 服务器

训练用 RTX 5060 Ti，SSH 信息运行时从 `.claude/settings.json` 定时任务中获取（不在 memory 中硬编码密码）。

## 阿里云 ECS 部署

- 前端: `http://120.27.15.235` — Vue3 SPA，nginx 托管
- 后端: FastAPI `server_light.py`，systemd `algae-image.service`，端口 8000
- 详见 handoff: `docs/Temp/handoff-20260609-v2-arch-deploy.md`

## 关键设计文档

- CLAUDE.md: `E:\code\algaeimage\CLAUDE.md`
- code/README.md: 完整目录地图和权重清单
- docs/handoff-20260524-algae-guardian-v1.md: V1 构建交接文档
- docs/v1_product_build_0524.md: V1 产品构建日志

## 竞赛文书 (2026 光电设计竞赛)

- 旧策划书: `项目文书/策划书——藻影知微队.pdf`
- 旧PPT: `项目文书/藻影知微——水下偏振原位智能成像系统.pptx`
- 新技术方案: `项目文书/技术方案——藻影知微.md` + `.docx`
- 技术文书智能体: `.claude/agents/algae_technical_writer.agent.md`

## 模型权重位置

- RDN: `algae_image_v1/weights/rdn_polarization.pth` (PSNR 62.46dB)
- YOLO v8l: `algae_image_v2/weights/best_v8l.pt` (mAP50 42.9%)
- YOLO v8s: `algae_image_v2/weights/best_v8s.pt` (mAP50 73.9%)
- 权重不在 git 中，由 Git LFS 追踪
