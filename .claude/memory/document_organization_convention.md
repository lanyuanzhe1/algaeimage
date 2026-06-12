---
name: document-organization-convention
description: 文档目录结构与命名规范 — 统一 MM-DD_ 前缀，按时间线索引
metadata:
  type: project
---

# 文档组织规范

## 核心约定

- **所有项目级文档**集中在 `docs/`，统一使用 `MM-DD_描述.md` 命名。
- 按文件名排序即得到时间线，`docs/README.md` 是完整索引表。
- 各代码子目录（`code/algae_image_v1/docs/`、`code/algae_image_v2/docs/` 等）文档独立保留，不归入 `docs/`。

## 目录结构

```
docs/
├── README.md                         ← 时间线索引
├── MM-DD_*.md / *.docx               ← 项目文档（训练报告、调研、构建日志、答辩等）
├── reference/                        ← 外部参考资料（论文 PDF、商业计划书、竞赛文件）
└── superpowers/                      ← AI agent 生成的设计规格 (specs/) 与实施计划 (plans/)
```

其他文档原地保留的位置：
- `项目文书/` — 竞赛技术方案（md + docx + pdf）
- `code/README.md` — 代码目录地图
- `CLAUDE.md` — AI agent 项目指引

## 新建文档规则

1. 文件名：`MM-DD_简短英文描述.md`，如 `06-12_algae-classification-experiment.md`
2. 在 `docs/README.md` 时间线表格中新增一行
3. 如果是外部参考材料，放入 `docs/reference/`

**Why:** 之前文档散落在 15+ 个目录，日期格式有 4 种（`0507`/`20260523`/`2026-05-25`/无日期），根目录也有游离文件。统一后只需看 `docs/README.md` 一个入口。

**How to apply:** 
- 写新文档时使用 `docs/MM-DD_slug.md` 格式
- 发现游离文档时移入 `docs/` 并重命名
- AI agent 生成的 specs/plans 放入 `docs/superpowers/` 保持不变
