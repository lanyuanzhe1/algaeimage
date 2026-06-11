# 样机演示流程 — 设计文档

**日期**: 2026-06-11
**分支**: HSV
**状态**: 已确认

---

## 目标

搭建样机演示流程：电脑连接海康工业相机 → 自动采集 → 实时检测 → 前端展示。后续 Docker 封装迁移。

## 硬件

- 相机: 海康 MV-CA013-20GC (1.3MP GigE 彩色)
- SDK: MVS Python SDK (Development/ 目录，DLL + ctypes 封装)

## 架构

```
相机 (GigE) → Python SDK callback → numpy frame → POST /api/v1/detect → core_engine 管线 → 前端轮询展示
```

### 组件

| 组件 | 文件 | 说明 |
|------|------|------|
| 相机采集器 | `camera_grabber.py` | SDK 回调取帧，节流后 POST 到 backend |
| 视频采集器 | `video_grabber.py` | cv2 读 AVI，模拟相机输出，开发测试用 |
| Backend (已有，微调) | `backend/app/` | 新增 `GET /detect/latest` + `GET /detect/stream-status` |
| 前端 (已有，微调) | `frontend/src/` | DetectPage 实时模式，setInterval 2s 轮询 |

### 数据流

1. camera_grabber.py: `MV_CC_RegisterImageCallBackEx2` 回调 → `MV_CC_ConvertPixelTypeEx` → `numpy.frombuffer` → RGB numpy array
2. 帧率控制: 相机 ~8.8fps，回调中按时间间隔节流（默认不丢帧，可配）
3. HTTP POST multipart/form-data 到 `POST /api/v1/detect`（复用现有单图检测接口）
4. Backend 运行管线，结果存内存 buffer（最近 N 条）
5. 前端 2s 轮询 `GET /api/v1/detect/latest`，自动更新 PipelineViz + ResultTable

### 双模式

- **实时模式** (有相机): camera_grabber.py 直连 SDK
- **回放模式** (无相机): video_grabber.py 读 AVI 文件，按帧率逐帧 POST

两种模式共用同一 POST /api/v1/detect 接口，backend 和前端不区分来源。

## 新增 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/detect/latest?n=10` | 返回最近 N 条检测结果 |
| GET | `/api/v1/detect/stream-status` | 采集状态：fps、总帧数、运行时间 |

## 前端改动

- DetectPage: 新增"实时监测"开关
- 开启后: 隐藏手动上传区，显示实时 PipelineViz + ResultTable + 状态栏
- setInterval 2000ms 调 `/detect/latest` 刷新数据
- 新增小型状态栏: 当前 fps、已处理帧数、最近检测到藻类

## Docker 策略 (后续)

- camera_grabber.py 在 Windows 宿主机运行（依赖 MvCameraControl.dll）
- backend + Vue3 + nginx 打包 Linux Docker 镜像
- 样机迁移: 宿主机安装 SDK 运行时 → 启动 grabber → docker compose up

## 约束

- SDK DLL 仅 Windows x64，Docker 仅封装 Linux 部分
- 相机需 GigE 网络连接，样机现场需配置 IP
- 管线处理耗时约 0.1-0.3s/帧（YOLO 推理），8.8fps 相机帧率不会拥塞

## 文件规划

```
code/algae_image_v2/
├── camera_grabber.py          # 新增: SDK 采集器
├── video_grabber.py           # 新增: AVI 回放采集器
├── backend/app/
│   ├── routes/detection.py    # 修改: 加 /detect/latest + /detect/stream-status
│   └── services/stream_state.py  # 新增: 内存状态管理
├── frontend/src/
│   └── views/DetectPage.vue   # 修改: 加实时模式
```
