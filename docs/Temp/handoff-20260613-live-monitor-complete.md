# Handoff: 样机演示实时监测 — 全链路贯通 + 性能优化

**日期**: 2026-06-13
**分支**: `HSV`
**最新 commit**: `2364e68`

---

## 当前状态

样机演示全链路贯通：海康相机 SDK 直连 → 一键启动采集 → 双栏实时展示 → 历史页自动刷新。

| 组件 | 状态 | 备注 |
|------|------|------|
| 相机 SDK 集成 | ✅ | 集成进 backend 进程，`CameraController` 类 |
| 一键启动 | ✅ | 前端按钮 → `POST /stream/start` → worker 线程自动采集 |
| 双栏展示 | ✅ | 左：原始采集图，右：YOLO 标注图 |
| 跨页面保持 | ✅ | Store 管理轮询生命周期，切页不中断 |
| 历史自动刷新 | ✅ | 3s 轮询 + camera worker 批量写 DB |
| 时间戳 | ✅ | UTC+8 修复 |
| 性能优化 | ✅ | run_ndarray + JPEG + 批量 DB（~1.5-1.8fps 预期） |

## 关键实现细节

### 架构
```
SDK callback → frame queue → worker thread
    → pipeline.run_ndarray(frame)  # 无磁盘 I/O
    → save raw.jpg + result.jpg (JPEG quality 90)
    → stream_state.add_result()
    → batch DB insert (every 10 frames)
    → GET /detect/latest (2s polling) → LiveMonitor.vue
```

### Camera worker 性能优化（commit `d03affe`）
- `run_ndarray()`: 跳过 temp 文件 I/O（省 1 写 + 1 读 + 1 删）
- JPEG quality 90 替代 PNG: 编码快 5-10x
- 批量 DB 写入: 每 10 帧一次 `executemany`

### 时间戳修复（commit `2364e68`）
- 根因: 实际表用 `CURRENT_TIMESTAMP`（UTC），不是 database.py 写的 `localtime`
- 修复: camera worker 显式设 `time.localtime()` + DB default 改 `datetime('now','+8 hours')`

## 启动命令

```bash
conda activate ican
cd e:/code/algaeimage/code/algae_image_v2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# 浏览器 → http://localhost:8000/app/detect/live → 点击"开始采集"
```

## 关键路径

- 相机 DLL: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64`
- MVS SDK: `A:\Program Files\MVS\Development\Samples\Python\MvImport`
- Node.js: `A:\Program Files\nodejs\`
- DB: `backend/data/history.db`
- Live images: `backend/data/results/live/` (JPEG, 50帧缓存)

## 已知坑点

- MVS 客户端与 SDK 互斥（`0x80000203`）
- npm 不在 bash PATH，前端构建需用 `cmd.exe //c` 方式
- 前端 dist/ 在 .gitignore 中，更新需 `git add -f`
- `.claude/skills/` 有 14 个过时目录引用（Mac symlink 遗留，warning 无害）

## 相关文档

- 设计 spec: `docs/superpowers/specs/2026-06-12-demo-live-monitor-design.md`
- 实施计划: `docs/superpowers/plans/2026-06-12-demo-live-monitor.md`
- CLAUDE.md: V2 样机演示段（含相机 SDK、已知坑点）

## 建议 Skills

- `superpowers:brainstorming` — 如需继续架构讨论
- `superpowers:subagent-driven-development` — 实现新功能
- `write_log` / `write-memory` — 记录技术细节
