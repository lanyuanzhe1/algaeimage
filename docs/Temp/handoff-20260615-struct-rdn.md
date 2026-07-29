# Handoff: 结构张量+RDN 管线迁移完成

**日期**: 2026-06-15
**分支**: `HSV`
**状态**: 管线已升级，LiveMonitor bug 已修复，服务器已停止

---

## 会话成果

### 1. 管线迁移（核心交付）

V2 样机管线从 HSV 偏振替换为结构张量+RDN+YOLOv8s：

```
旧: RGB → HSV偏振(0.65s)       → (skip RDN) → I_enh(α=0.05) → YOLOv8l → 35.4% mAP50
新: RGB → 结构张量偏振(0.24s)   → RDN(2.3s)  → I_enh(α=0.60) → YOLOv8s → 73.9% mAP50
```

实验依据（`code/RDN_HSV_0526/README.md`）：5 组 FMPD 对照实验，结构张量+RDN 是最优组合。HSV+RDN 反而有害（33.0% < 35.4%）。

### 2. 速度剖析与优化

| 分辨率 | 偏振 | RDN | I_enh | YOLO | 总耗时 |
|--------|------|-----|-------|------|--------|
| 2080×1540 | 0.9s | 320s | 0.5s | 1.1s | 322s |
| 1024×758 | 0.2s | 2.3s | 0.07s | 0.1s | 2.7s |
| 640×474 | 0.08s | 0.6s | 0.03s | 0.2s | 0.9s |

`PIPELINE_MAX_WIDTH=1024`（`core_engine/config.py`）作为默认值。若需 >1fps 改 640。

### 3. LiveMonitor Bug 修复

- **Bug 1 停止按钮无效**: `store.stop()` API 失败时状态不重置。修复: try/catch 包裹 API，`isStreaming`/`streamMode` 始终重置
- **Bug 2 切 Tab 状态丢失**: 组件本地 `state` ref 与 Pinia store 断开。修复: `onMounted` 检查 `store.isStreaming` 恢复状态
- 测试: `frontend/src/__tests__/detect-store.test.js`（6 tests, vitest + jsdom）

### 4. CLAUDE.md 更新

审计修正：管线描述、默认模型、SKIP_RDN、I_enh 参数、视频流端点、vitest 测试、conda 路径、云训练监控状态、LiveMonitor 坑点

### 5. Memory 更新

`project_context.md` + `demo_workflow_architecture.md` 已更新管线信息、速度数据、LiveMonitor 修复

---

## 关键路径

| 路径 | 说明 |
|------|------|
| `e:/code/algaeimage/code/algae_image_v2/` | V2 项目根 |
| `e:/code/algaeimage/code/algae_image_v2/core_engine/config.py` | SKIP_RDN, DEFAULT_MODEL, PIPELINE_MAX_WIDTH, IENH params |
| `e:/code/algaeimage/code/algae_image_v2/backend/app/services/pipeline.py` | PipelineRunner（RDN+resize） |
| `e:/code/algaeimage/code/algae_image_v2/backend/app/main.py` | RDN 加载注入 |
| `e:/code/algaeimage/code/algae_image_v2/weights/rdn_polarization.pth` | RDN 权重（PSNR 62.46dB, ~2.5MB） |
| `e:/code/algaeimage/code/algae_image_v2/weights/best_v8s.pt` | YOLOv8s FMPD 5-class（~22MB） |
| `e:/code/algaeimage/code/algae_image_v2/frontend/src/stores/detect.js` | Pinia store（stop 可靠性） |
| `e:/code/algaeimage/code/algae_image_v2/frontend/src/views/LiveMonitor.vue` | 实时监测组件 |
| `e:/code/algaeimage/code/RDN_HSV_0526/README.md` | 5 组实验对比数据 |
| `A:/Anaconda_envs/envs/ican/python.exe` | conda 环境 Python |

---

## 正确启动流程

```bash
# 1. 清理僵尸进程
python -c "import subprocess, os, signal; ..."

# 2. 启动后端（1024px resize + RDN + YOLOv8s）
cd e:/code/algaeimage/code/algae_image_v2
"A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 3. 等待就绪（~15s RDN + YOLO 加载）
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs  # 期望 200

# 4. 浏览器访问
# 手动检测: http://localhost:8000/app/detect
# 实时监测: http://localhost:8000/app/detect/live（切到视频演示Tab）
```

**端口冲突**: 若 8000 被 TIME_WAIT 占用，换 8001/8002。120s 后自动释放。

---

## 当前代码状态

| 组件 | 状态 |
|------|------|
| 分支 | `HSV`，11+ commits ahead of main |
| 后端 | ⬜ 已停止 |
| 前端 dist | ✅ 已重建（commit `680405f`），含 LiveMonitor 修复 |
| 测试（Python） | 14 tests, 3 pre-existing failures（V1→V2 迁移问题） |
| 测试（前端） | 6/6 vitest pass |

---

## 已知问题

1. **RDN 速度**: 2.3s/帧（1024px），瓶颈在 DenseLayer concat 通道膨胀。考虑 ONNX 导出
2. **mAP50 虚高**: YOLOv8s 73.9% 是 train=val，真实泛化未知
3. **端口 TIME_WAIT**: `taskkill` 后 120s 残留，换端口绕过
4. **Python pipeline tests 3/14 fail**: 预存在的 V1→V2 迁移问题（LIFEWATCH_95_CLASSES 等）

---

## 建议技能

下一轮 agent 开始前建议 invoke:
- `memory` — 检查记忆文件获取完整项目上下文
- `superpowers:using-superpowers` — 技能发现入口
- `superpowers:brainstorming` — 如需扩展功能（RDN 加速、数据集扩充、模型重训）
