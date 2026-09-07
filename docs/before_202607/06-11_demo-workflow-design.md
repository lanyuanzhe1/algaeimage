# 样机演示流程 — 设计阶段

**日期:** 2026-06-11
**分支:** HSV

## 完成事项
- 评估 4 种相机控制方案，确定 Python SDK 直控路线
- 确认硬件型号 MV-CA013-20GC (GigE, 1.3MP 彩色)，SDK 完整可用
- 识别 SDK 关键能力：`MV_CC_RegisterImageCallBackEx2` 回调 + `MV_CC_ConvertPixelTypeEx` → numpy array
- 设计整体架构：SDK 回调 → numpy → POST /api/v1/detect → 前端 2s 轮询
- 确认双模式：实时模式 (SDK) + 回放模式 (AVI 视频)
- Memory 迁移：8 个用户级 memory 迁移至项目 `.claude/memory/`（git 同步）

## 技术细节

### 相机 SDK
- 型号: MV-CA013-20GC (海康机器人)
- SDK: `Development/` 目录，Python ctypes 封装
- 关键文件:
  - `Development/Samples/Python/MvImport/MvCameraControl_class.py`
  - `Development/Samples/Python/OpenCV/Grab_Callback_Cv/Grab_Callback_Cv.py`
  - `Development/Libraries/win64/MvCameraControl.lib`
- 参考示例: Grab_Callback_Cv 展示了完整链路：回调 → HB解码 → 像素转换 → numpy → cv2

### 架构决策
- 进程分离: camera_grabber 独立进程（持有 SDK cam 句柄），通过 HTTP POST 送帧到 backend
- 前端轮询: 2s 间隔 `GET /api/v1/detect/latest`，不引入 WebSocket
- 帧率: 相机硬件 ~8.8fps，回调中可配节流，默认不丢帧
- Docker 边界: SDK DLL 仅 Windows x64，grabber 在宿主机运行；backend + Vue3 + nginx 容器化

### 设计文档
- `docs/superpowers/specs/2026-06-11-demo-workflow-design.md`

### Memory 体系
- 项目 `.claude/memory/` 10 个记忆文件，覆盖偏好、参考、项目状态
- 用户级 `~/.claude/projects/.../memory/` 已清理，指向项目目录

## 遇到的问题
- Visual companion 服务器启动失败：Codex 环境的 node 不在默认 PATH，需指定 `C:\Users\HP\.cache\codex-runtimes\...\node\bin\node.exe` (v24.14.0)
- 服务器超时自动退出，重启后恢复

## 结果/产出
- 设计文档: `docs/superpowers/specs/2026-06-11-demo-workflow-design.md`
- 新增文件规划:
  - `code/algae_image_v2/camera_grabber.py` — SDK 采集器
  - `code/algae_image_v2/video_grabber.py` — AVI 回放采集器
  - `code/algae_image_v2/backend/app/services/stream_state.py` — 内存状态管理
- 修改文件规划:
  - `backend/app/routes/detection.py` — 加 `/detect/latest` + `/detect/stream-status`
  - `frontend/src/views/DetectPage.vue` — 加实时模式

## 下一步
- 写实现计划 (writing-plans)
- 先实现 video_grabber.py（用样本 AVI 跑通全流程，不依赖相机硬件）
- 再实现 camera_grabber.py（需相机连接测试）
- Backend + 前端改动
