# Handoff: 样机演示系统 — 视频源 + 曝光控制

**日期**: 2026-06-14
**分支**: `HSV`
**焦点**: 外场实验准备 — 视频演示模式、FMPD 数据集回放、相机曝光控制

---

## 会话成果

### 1. 视频演示模式（核心交付）

用视频文件替代相机作为检测输入源，完整架构：

```
前端 → POST /detect/stream/start-video { video_path, fps, loop }
    → VideoController (新建, backend/app/services/video.py)
    → cv2.VideoCapture 逐帧读取 → PipelineRunner.run_ndarray()
    → stream_state.add_result() → 保存 raw/result JPEG
    → 前端 GET /detect/latest 2s 轮询 → <img> 双栏渲染
```

**新建文件**:
- `code/algae_image_v2/backend/app/services/video.py` — VideoController 类（~200行），worker 线程模式，DB 批量写入，stream_state 复用

**修改文件**:
- `code/algae_image_v2/backend/app/routes.py`
  - `POST /detect/stream/start-video` — 启动视频流（`video_path`, `fps`, `loop` 参数）
  - `POST /detect/stream/stop-video` — 停止视频流
  - `GET /detect/video-list` — 动态扫描 `video/` 目录返回 mp4 列表
  - `GET /detect/video-status` — 视频流状态
  - `_resolve_video_path()` — 解决 Windows GBK/UTF-8 中文文件名编码问题（数字前缀回退匹配）
- `code/algae_image_v2/backend/app/main.py`
  - lifespan 注册 VideoController，注入 pipeline_runner + live_dir
- `code/algae_image_v2/frontend/src/api/index.js` — +4 个 API 函数
- `code/algae_image_v2/frontend/src/stores/detect.js`
  - `streamMode` ref（'camera'|'video'|null）
  - `startVideo()` / `fetchVideoList()` actions
  - `videoPath` / `videoFps` / `videoLoop` / `videoOptions` refs
  - `stop()` 自动识别模式调对应停止 API
- `code/algae_image_v2/frontend/src/views/LiveMonitor.vue`
  - 双 Tab 布局：`el-tabs` → 「相机采集」|「视频演示」
  - 相机 Tab：曝光滑块 + 开始采集
  - 视频 Tab：下拉选视频（动态列表）+ FPS + 循环开关 + 视频演示按钮
  - `onMounted` 自动 fetchVideoList()，不自动启动流
  - 停止按钮对两种模式通用

### 2. 相机曝光控制

- `camera.py`: `start(exposure_us=5000)` → 关自动曝光 + `SetFloatValue("ExposureTime")`
- `routes.py`: `stream/start?exposure_us=` 查询参数
- 前端 store: `exposureUs` ref (100-50000 μs)
- LiveMonitor: 曝光 slider（仅在相机 Tab 显示）

### 3. FMPD 数据集视频

293 张 FMPD TIFF 原图（2080×1540）→ `video/04_fmpd_dataset.mp4`（53.5MB，2fps，2分26秒循环）

### 4. 视频文件重命名

中文文件名导致 Windows GBK/HTTP UTF-8 编码不匹配 → 改为英文：
```
1_水样玻片.mp4         → 01_water_sample.mp4  (已删除，用户替换)
2_溶液中的藻类慢速流动.mp4 → 02_algae_flow.mp4   (已删除，用户替换)
5_较好的，杂乱且流动.mp4  → 03_algae_clutter.mp4 (已删除，用户替换)
新增: 04_fmpd_dataset.mp4 (54MB, 293帧, 2fps)
```

当前 video/ 目录内容（动态扫描）:
- `04_fmpd_dataset.mp4` (54MB)
- `11_藻液与水草那瓶藻晃动.mp4` (14MB) — 中文名，数字前缀匹配
- `14_最后录的一版的短视频.mp4` (3MB)
- `8_藻液静置.mp4` (1MB)

### 5. 存储清理

- `dist-release/` (8.44GB) → 封存为 `dist-release_20260528.zip` (6.23GB)
- `backend/data/results/` (781MB) + `uploads/` (267MB) 未清理（按需）

### 6. 僵尸进程模式

bash TaskStop 不杀 Python 子进程 → SDK 句柄悬挂。清理脚本已写入 `field_startup_guide.md` 记忆：
```python
import os, signal, subprocess
r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], ...)
os.kill(pid, signal.SIGTERM)
```

---

## 当前运行状态

| 组件 | 状态 |
|------|------|
| 后端 `:8000` | 🟢 运行中 |
| 前端 | 🟢 已打开 `http://localhost:8000/app/detect/live?v=8` |
| 视频流 | ⬜ 空闲，等待用户点击 |

---

## 正确启动流程（外场实验）

```bash
# 0. 清理僵尸
"A:/Anaconda_envs/envs/ican/python.exe" -c "...tasklist...os.kill..."

# 1. 启动后端
cd e:/code/codex/code/algae_image_v2
"A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# 2. 等待就绪 (YOLO 加载 ~15s)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs  # 期望 200

# 3. 打开浏览器
"A:/Anaconda_envs/envs/ican/python.exe" -c "import webbrowser; webbrowser.open('http://localhost:8000/app/detect/live')"

# 4. 用户手动操作
#    - Ctrl+Shift+R 硬刷新
#    - 切到「视频演示」Tab
#    - 选视频 → 调 FPS=2 → 勾循环 → 点「视频演示」
```

**千万别做**:
- 不要用 `curl` 预启动相机/视频 → 前端轮询不会启动
- 不要用 `camera_grabber.py` 独立采集 → 与前端 CameraController 冲突
- 不要用 bash `TaskStop` 关进程 → 僵尸残留

---

## 关键路径

| 路径 | 说明 |
|------|------|
| `e:/code/codex/code/algae_image_v2/` | V2 项目根 |
| `e:/code/codex/video/` | 视频文件目录（repo root 下） |
| `A:/Anaconda_envs/envs/ican/python.exe` | conda 环境 Python |
| `A:/Program Files/nodejs/npm.cmd` | 前端构建 |

---

## 相关记忆文件

- `e:\code\codex\.claude\memory\field_startup_guide.md` — 外场启动完整流程 + 避坑
- `e:\code\codex\.claude\memory\conda_bash_path_fix.md` — bash 中 conda 不可用的根因
- `e:\code\codex\.claude\memory\demo_workflow_architecture.md` — 样机架构
- `e:\code\codex\.claude\memory\MEMORY.md` — 总索引

---

## 待办 / 已知问题

1. **前端曝光滑块未在 dist 中** — 源码已写，dist 已构建（2026-06-14 20:16），需 Ctrl+Shift+R 硬刷新
2. **VideoController 和 CameraController 不能同时运行** — 共享同一套 stream_state + live_dir，同时启动会互相覆盖
3. **FPS 偏低** — 实际 0.8-1.7fps，目标 2-10fps。瓶颈在 YOLOv8l GPU 推理 (~600-800ms/帧)
4. **`_resolve_video_path` 数字前缀匹配** — 对中文文件名有效，但如果两个文件数字前缀相同会选错
5. **前端 dist 构建需 Windows cmd 方式** — `A:/Program Files/nodejs/npm.cmd`，PATH 需含 nodejs

---

## 建议技能

下一轮 agent 开始前建议 invoke:
- `superpowers:using-superpowers` — 技能发现入口
- `superpowers:brainstorming` — 如需扩展功能（如多视频对比、录制回放）
- `memory` — 检查记忆文件获取完整项目上下文
