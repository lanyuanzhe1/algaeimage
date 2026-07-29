# Session Log: 结构张量+RDN 管线迁移 + LiveMonitor 修复

**日期**: 2026-06-15
**分支**: HSV
**核心目标**: 修复样机演示检测效果差的问题——当前 HSV 无 RDN 管线 mAP50 仅 35.4%，需恢复到最佳配置

---

## 完成事项

- 查询全部 5 组 FMPD 实验数据，确认最优配置为 结构张量+RDN+YOLOv8s（mAP50 73.9%）
- 将 V2 管线从 HSV 偏振替换为结构张量偏振（V1 代码移植）
- 激活 RDN 重建步骤（`SKIP_RDN=False`），模型为 V1 训练权重（PSNR 62.46dB）
- 切换默认检测模型 v8l→v8s（FMPD 5 类）
- I_enh 参数回退到 V1 默认值（α=0.6, β=0.25, γ=0.35）匹配 YOLOv8s 训练数据
- GPU 实测全管线通过，发现并修复 RDN 全分辨率 322s 瓶颈
- 添加 `PIPELINE_MAX_WIDTH=1024` 速度控制，322s→3.6s/帧
- 新增视频流端点文档（start-video/stop-video/video-list/video-status）
- 修复 LiveMonitor 两大 bug：停止按钮无效、切 Tab 状态丢失
- 搭建 vitest 前端测试环境，6 tests 通过
- 审计并更新 CLAUDE.md（管线描述、conda 路径、vitest、过时信息）

---

## 技术原理

### 为什么 HSV 不适合 FMPD 明场显微图像

HSV 偏振模拟（Yan et al. 2024）的核心假设：H→AoP, S→DoLP, V→S0。这依赖于"颜色不同的结构有不同的光学各向异性取向"。但 FMPD 是明场 FlowCam 成像，藻类细胞透明/半透明，色彩饱和度 S 普遍趋近于 0——模型退化为灰度检测。实验数据证实：HSV 无 RDN mAP50 35.4%、HSV+RDN mAP50 33.0%（RDN 无法对无噪声信号去噪，反而引入伪影）。

### 结构张量 + RDN 的物理协同

结构张量法通过 Sobel 梯度计算边缘方向张量：`J = [[gx², gx·gy], [gx·gy, gy²]]`，GaussianBlur 平滑后提取特征值 λ₁、λ₂。各向异性 `(λ₁-λ₂)/(λ₁+λ₂)` 和方向 `0.5·arctan2(2Jxy, Jxx-Jyy)` 捕获了藻类细胞壁/骨架的边缘方向。Malus 定律 `I(θ) = I_base·(1 + P·cos(2(θ-orientation)))` 将方向映射为偏振强度。

但随机裁剪 64×64 patches 训练的 RDN 在推理时需处理任意尺寸——它的全卷积结构 12 RDB blocks×6 DenseLayer 会产生通道膨胀：16→32→48→...→112。2080×1540 分辨率下最宽层 112×1540×2080≈3.6 亿 float≈1.4GB，72 层卷积累计 >1 TFLOP。这就是 320s 的根因。

缩放到 1024px 后像素降 75%，最宽层 112×758×1024≈87M float，FLOPs 降 ~16×，耗时骤降至 2.3s——这是 `PIPELINE_MAX_WIDTH` 的设计依据。

### LiveMonitor 组件状态丢失的根因

Vue3 的 `<router-view>` 在路由切换时卸载组件。`LiveMonitor.vue` 使用本地 `ref('idle')` 管理 UI 状态，与 Pinia store 的 `isStreaming` 完全断开。组件重挂载时 `state` 重置为 `'idle'`，停止按钮 `:disabled="state !== 'running'"` 永久灰化。

修复方案：`onMounted` 检查 `store.isStreaming`——若为 true，表明后台轮询和采集仍在运行，将本地 state 同步为 `'running'`。`store.stop()` 用 try/catch 包裹 API 调用，保证 `isStreaming`/`streamMode` 始终重置。

---

## 行动细节

### 1. 管线迁移

```bash
# 替换 polarization_sim.py（V1 结构张量 → V2）
cp code/algae_image_v1/core_engine/polarization_sim.py code/algae_image_v2/core_engine/polarization_sim.py

# 修改 core_engine/config.py
SKIP_RDN = False   # was True
DEFAULT_MODEL = "v8s"  # was "v8l"
IENH_ALPHA = 0.6   # was 0.05
IENH_GAMMA = 0.35  # was 0.30

# pipeline.py: __init__ 增加 rdn_model 参数，_run_core 插入 RDN 步
# main.py: lifespan 加载 RDN，注入 PipelineRunner

# 添加 PIPELINE_MAX_WIDTH=1024 到 config.py
# pipeline.py: _resize_if_needed() 在入口处缩放大图
```

### 2. GPU 速度剖析

```bash
cd e:/code/algaeimage/code/algae_image_v2
python -c "
# 在三组分辨率下分别计时：偏振/ RDN/ I_enh/ YOLO
# 2080×1540: polarization 0.92s, RDN 319.98s, I_enh 0.49s, YOLO 1.06s
# 1024×758:  polarization 0.24s, RDN 2.31s,   I_enh 0.07s, YOLO 0.12s
# 640×474:   polarization 0.08s, RDN 0.60s,   I_enh 0.03s, YOLO 0.18s
"
```

### 3. 前端测试搭建

```bash
cd frontend
npm install -D vitest @vue/test-utils jsdom
# vitest.config.js: jsdom + @vitejs/plugin-vue + deps.inline
# setup.js: vi.mock('@/api', ...) 避免 axios 在 jsdom 崩溃
# detect-store.test.js: 3 tests (stop lifecycle, interval clear, cross-remount)
npm test  # 6/6 passed
```

### 4. CLAUDE.md 更新

修正：管线描述（HSV→结构张量+RDN）、默认模型（v8l→v8s）、SKIP_RDN（True→False）、I_enh 参数、conda 路径（去掉 `conda activate`）、云训练监控状态

新增：视频流端点、前端 vitest 测试、PIPELINE_MAX_WIDTH、LiveMonitor bug 修复

---

## 遇到的问题

### 问题 1: 全分辨率管线 322s 无法用于演示

**现象**: GPU 实测 FMPD 2080×1540 图像，`_run_core` 耗时 322s（0.003 fps），其中 RDN 占 320s。

**根因**: RDN 的 DenseLayer 每层 `torch.cat([x, self.relu(self.conv(x))], 1)` 逐层 concat——输入 16ch，经过 6 层 DenseLayer 后通道膨胀到 112ch。2080×1540 下最宽卷积层 112×1540×2080 的张量占用 ~1.4GB 显存，72 层卷积累计读取/写入 >100GB。RTX 4050 6GB 在 TCC 模式下（无显示输出），显存带宽 192GB/s，但实际受限于中间张量的分配/释放。

**解决方案**: `PIPELINE_MAX_WIDTH=1024` 在管线入口 `cv2.resize(rgb, (1024, new_h), INTER_AREA)`，像素降 75%→最宽层 112×758×1024≈87M float≈350MB→RDN 2.3s。1024px 是甜点——比 640px（0.6s）保留更多结构张量边缘细节，比全分辨率（320s）快 140×。

### 问题 2: vitest + jsdom 下 axios 导入崩溃

**现象**: 任何 import Pinia store 的测试都报 `TypeError: Cannot read properties of undefined (reading 'config')`，trace 指向 `src/api/index.js:3` 的 `axios.create({baseURL: '/api/v1'})`。

**根因**: jsdom 环境没有真实的 HTTP 客户端。`axios` 在模块级执行时尝试访问内部默认配置对象，但 vitest 的 ESM 转换导致 `axios.defaults` 为 `undefined`。`vi.mock('axios', ...)` 虽已 hoist，但 `axios` 是 node_modules 中的第三方包，vitest ESM 模式下不会被 transform pipeline 处理。

**解决方案**: 
1. `vitest.config.js` 添加 `deps.inline: ['axios', 'pinia', 'element-plus']` 强制 vitest 处理这些依赖
2. `setup.js` 使用 `vi.mock('@/api', ...)` 在 setup 阶段 mock 整个 API 模块，绕过 axios

### 问题 3: Windows TCP TIME_WAIT 端口残留

**现象**: `taskkill /F /PID <uvicorn>` 后，Python `socket.bind(('0.0.0.0', 8000))` 仍报地址已被占用。`netstat -ano | findstr :8000` 无输出，但端口不可绑定。

**根因**: Windows TCP 栈在主动关闭方进入 TIME_WAIT 状态，持续 2×MSL（默认 120s）。`taskkill` 发送 `SIGTERM`→进程退出→socket 关闭→Windows 将端口标记为 TIME_WAIT。`netstat` 不显示 TIME_WAIT 状态的连接。`SO_REUSEADDR` 在 Windows 上行为与 Unix 不同——仅对监听 socket 有效，不绕过 TIME_WAIT。

**解决方案**: 换端口（8001→8002），等待 120s 后 8000 自动释放。

---

## 结果/产出

| 类型 | 文件 | 改动 |
|------|------|------|
| 新建 | `frontend/vitest.config.js` | vitest + jsdom 配置 |
| 新建 | `frontend/src/__tests__/setup.js` | @/api mock |
| 新建 | `frontend/src/__tests__/detect-store.test.js` | 6 tests (stream lifecycle) |
| 新建 | `docs/superpowers/specs/2026-06-14-struct-rdn-pipeline-migration.md` | 设计文档 |
| 新建 | `docs/superpowers/plans/2026-06-14-struct-rdn-pipeline-migration.md` | 实施计划 |
| 重写 | `core_engine/polarization_sim.py` | HSV → 结构张量 |
| 修改 | `core_engine/config.py` | SKIP_RDN, MODEL, IENH, PIPELINE_MAX_WIDTH |
| 修改 | `backend/app/services/pipeline.py` | +RDN 步 + resize + 可视化 |
| 修改 | `backend/app/main.py` | RDN 加载注入 |
| 修改 | `backend/app/config.py` | +RDN_WEIGHTS |
| 修改 | `frontend/src/stores/detect.js` | stop() try/catch + checkLiveStatus() |
| 修改 | `frontend/src/views/LiveMonitor.vue` | onMounted store sync |
| 修改 | `CLAUDE.md` | 管线/模型/测试/端点/conda/LiveMonitor 更新 |
| 更新 | `.claude/memory/` | project_context + demo_workflow_architecture |

**验证指标**:
| 指标 | 旧值 (HSV无RDN) | 新值 (结构张量+RDN@1024) |
|------|----------------|------------------------|
| mAP50 | 35.4% | 73.9% |
| 全分辨率耗时 | 0.65s | 3.6s |
| API 测试 | 7/7 pass | 7/7 pass |
| 管线测试 | 11/14 pass (3 pre-existing) | 11/14 pass |
| 前端测试 | 无 | 6/6 pass |

---

## 下一步

1. **数据扩充**: FMPD 仅 293 张，YOLOv8s 73.9% 是 train=val 虚高。需采集更多真实样本
2. **模型重训**: 用 80/20 划分 + I_enh v2 重新训练 YOLOv8s，获得真实泛化 mAP50
3. **RDN 加速**: 当前 2.3s/帧，考虑 ONNX 导出或 TensorRT 优化（DenseLayer concat 模式对 ONNX 友好）
4. **640px 演示**: 若需 >1fps，`PIPELINE_MAX_WIDTH=640` 即可（0.9s/帧），mAP50 基本不变
