---
name: performance-patterns-camera-worker
description: 相机 worker 性能优化模式 — 避免磁盘往返、JPEG替代PNG、批量DB写入
metadata:
  type: feedback
---

## 相机实时采集性能优化模式

### 避免磁盘往返

Pipeline 接受文件路径时，不要先把 ndarray 写成 temp 文件再让 pipeline 读回去。应该在 PipelineRunner 上提供 `run_ndarray(rgb: np.ndarray)` 方法，直接传内存中的 ndarray。

**实测**: 省 ~200ms/帧（1 次 PNG 编码写 + 1 次 PNG 解码读 + 1 次文件删除）

### JPEG 替代 PNG 做实时预览

实时监测场景不需要 PNG 无损压缩。JPEG quality 90 编码速度快 5-10x，文件小 10-20x，画质差异肉眼不可分辨。

### 批量 DB 写入

不要每帧 open connection → execute → commit → close。用 `executemany()` 每 N 帧（推荐 10）批量写入一个事务。

### 线程模型

- SDK 回调线程只做解码 + push 到队列（`threading.Lock` 保护）
- Worker 线程取最新帧、跑 pipeline、存图、写 DB
- `stream_state` 读写分离（写端在 worker 线程，读端在 uvicorn async handler），`threading.Lock` 保证线程安全
- SQLite 同步连接在 worker 线程中使用（非 async），避免与 aiosqlite 竞争

**Why**: 初次实现 0.86fps，优化后 1.5-1.8fps，提升约 2x。瓶颈在 YOLOv8l GPU 推理（~500ms），不在 I/O。

**How to apply**: 写实时采集 worker 时优先考虑内存传递 ndarray、JPEG 预览格式、批量 DB 事务。
