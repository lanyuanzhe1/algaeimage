# Session Log — 2026-05-22

**日期:** 2026-05-22
**分支:** HSV

## 完成事项

- 记录 HSV LifeWatch 全流程管线到 auto-memory，从 docs 补充关键历史事件
- 全局 settings.json 新增 4 条 Bash allow 规则
- 创建 `write_log` 自定义 skill，用于编写工作日志/报告

## 技术细节

### 1. Auto-Memory 更新

**新增文件:** `C:\Users\HP\.claude\projects\E--code-codex\memory\hsv_lifewatch_pipeline.md`

从以下 docs 提取了完整上下文：
- `code/Polar_sim_0522/docs/design.md` — HSV 管线设计（Yan 2024 HSV 偏振方法）
- `docs/lifewatch_rdn_restart_20260520.md` — Stokes 计算 Bug 修复（RDN 4 通道 → 正确 Stokes 公式）
- `docs/yolov8s_rescue_report_20260521.md` — YOLOv8s epoch 19 达 mAP50=82.24% 后 AMP FP16 崩塌

记录的关键信息：
- 两台 GPU 服务器：RTX 5060 Ti (Polar_sim_0520) 和 Tesla V100 (Polar_sim_0522)
- I_enh v2 公式: `I_enh = Norm(S0 * (1 + α - γ·DoLP + β·|sin(2·AoP)|·DoLP))`, α=0.6, β=0.25, γ=0.35
- YOLO 训练必须禁用 `hsv_s/hsv_v` 保护偏振通道

**索引更新:** `MEMORY.md` 新增第 5 条指向

### 2. 全局权限配置

**文件:** `C:\Users\HP\.claude\settings.json`

新增 4 条 allow 规则：

| 规则 | 用途 |
|------|------|
| `Bash(sshpass *)` | GPU 服务器 SSH 连接 |
| `Bash(nvidia-smi *)` | GPU 状态监控 |
| `Bash(jq *)` | JSON 解析 |
| `Bash(cd *)` | 目录切换 |

全局现已累计 ~135 条 allow 规则。

### 3. write_log Skill

**文件:** `C:\Users\HP\.claude\skills\write_log\SKILL.md`

功能要点：
- 文件命名: `{名称}_{月日}.{ext}`（如 `skill_test_0522.md`），写前必须确认
- 默认 Markdown，说"Word/docx"时走 docx skill
- 内容必须来自实际会话记录，不准编造技术细节

## 结果/产出

| 类型 | 路径 |
|------|------|
| Memory | `hsv_lifewatch_pipeline.md` + `MEMORY.md` 更新 |
| 配置 | `~/.claude/settings.json` +4 allow 规则 |
| Skill | `~/.claude/skills/write_log/SKILL.md` |

## 下一步

- 继续 HSV 分支工作：`compare_rdn.py` 对比新旧 RDN 在 HSV 数据上的表现
- LifeWatch 管线部署到 Tesla V100 服务器
