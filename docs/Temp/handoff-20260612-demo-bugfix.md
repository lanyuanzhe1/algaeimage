# Handoff: 样机演示流程 — 实时监测 Bug 修复

**日期**: 2026-06-12
**分支**: `HSV`
**最新 commit**: `629571a`

---

## 当前状态

样机演示流程核心已贯通：海康 MV-CA013-20GC SDK 直连 → 5fps 采集 → YOLO 检测 → 前端展示。

| 组件 | 状态 | 备注 |
|------|------|------|
| camera_grabber.py | ✅ | SDK 直连，DLL 加载修复 |
| video_grabber.py | ✅ | AVI 回放，无相机测试用 |
| stream_state.py | ✅ | 线程安全，/detect/latest + /detect/stream-status |
| SPA fallback | ✅ | /app/{path:path} 路由 |
| 前端实时监测 | ❌ | 开关不触发轮询 |

## 核心 Bug：实时监测不刷新

**现象**: 点击导航栏"实时监测"开关，页面无变化，不显示实时数据。

**根因**: `App.vue` 中 `v-model="store.liveMode"` 与 `@change="store.toggleLiveMode"` 双重触发：
1. 用户点击 → `v-model` 写 `liveMode = true`
2. `@change` 触发 → `toggleLiveMode()` 读取 `liveMode.value`（已是 `true`）→ 取反设为 `false`
3. `startPolling()` 从未被调用

**修复**: 去掉 `@change`，在 `App.vue` `<script setup>` 添加：
```javascript
import { watch } from 'vue'
watch(() => store.liveMode, (val) => {
  if (val) store.startPolling(); else store.stopPolling()
})
```

相关文件：
- `code/algae_image_v2/frontend/src/App.vue` — 移除第 36 行 `@change="store.toggleLiveMode"`
- `code/algae_image_v2/frontend/src/stores/detect.js` — `toggleLiveMode` 可删除或保留作手动触发

## 演示启动命令

```bash
# 1. Backend
cd e:/code/codex/code/algae_image_v2
A:/Anaconda_envs/envs/ican/python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2. 相机采集（需先关闭 MVS 客户端）
A:/Anaconda_envs/envs/ican/python.exe camera_grabber.py --fps 5

# 3. 浏览器
http://localhost:8000/app/detect  → 导航栏点"实时监测"
```

## 关键路径

- 相机 DLL: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\MvCameraControl.dll`
- MVS SDK Python: `A:\Program Files\MVS\Development\Samples\Python\MvImport`
- Node.js: `A:\Program Files\nodejs\` （前端构建需 Python subprocess 调用）
- Conda: `ican`, `A:\Anaconda_envs\envs\ican`

## 已知坑点

- MVS 客户端与 SDK 互斥（`0x80000203`）
- 端口残留：换端口或用 `SO_REUSEADDR`
- history.db 可能被锁：重命名绕过
- npm 不在 bash PATH：用 Python subprocess 构建前端
- 前端 dist/ 在 .gitignore 中，更新需 force-add

## 下一步

1. 修复实时监测 bug（5 分钟，改动 2 行）
2. `npm run build` + 重启验证
3. Docker 封装（camera_grabber 宿主机，backend + nginx 容器）
4. 清理 `.claude/skills/` 14 个过时目录引用（Mac symlink 遗留）

## 参考文档

- 设计文档: `docs/superpowers/specs/2026-06-11-demo-workflow-design.md`
- 实现计划: `docs/superpowers/plans/2026-06-11-demo-workflow.md`
- 技术深度日志: `demo_workflow_tech_deep_0612.md`
- CLAUDE.md: 已更新 V2 样机演示段、相机 SDK、已知坑点

## 建议 Skills

- `superpowers:brainstorming` — 如需继续架构讨论
- `superpowers:subagent-driven-development` — 实现 bug 修复 + Docker
- `write_log` — 记录技术原理和行动细节
