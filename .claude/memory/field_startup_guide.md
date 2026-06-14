---
name: field-startup-guide
description: 外场实验正确启动流程，避免相机冲突与前端轮询不启动 — 2026-06-14
metadata:
  type: project
---

## 外场实验启动流程（已验证）

### 前置：清理僵尸进程

每次启动前，kill 所有残留 Python 进程（bash TaskStop 不会杀子进程）：

```bash
# 用 conda Python 杀僵尸（别用 bash taskkill）
"A:/Anaconda_envs/envs/ican/python.exe" -c "
import os, signal, subprocess
r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], capture_output=True, text=True)
for line in r.stdout.split('\n')[3:]:
    parts = line.split()
    if not parts or not parts[1].isdigit(): continue
    pid = int(parts[1])
    if pid != os.getpid():
        os.kill(pid, signal.SIGTERM)
        print(f'Killed {pid}')
"
```

### 正确启动顺序

```bash
# 1. 启动后端（后台）
cd e:/code/codex/code/algae_image_v2
"A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# 2. 确认后端就绪
sleep 6 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
# 期望: 200

# 3. 打开浏览器
"A:/Anaconda_envs/envs/ican/python.exe" -c "import webbrowser; webbrowser.open('http://localhost:8000/app/detect/live')"

# 4. 用户手动操作: 点击「开始采集」按钮
```

### 错误做法（已踩坑）

| 错误 | 后果 | 原因 |
|------|------|------|
| 用 `curl POST stream/start` 预启动相机 | 前端轮询不启动 + 用户点按钮时报 0x80000203 | `isStreaming=false`，前端不轮询；再 start 时相机已占 |
| 用 `camera_grabber.py --fps 5` 独立采集 | 同上：轮询不启动 + stream/start 冲突 | grabber 独占相机，前端 CameraController 无法打开 |
| 用 bash `TaskStop` 关进程 | Python 子进程残留，相机句柄不释放 | bash 被杀但 Python 子进程变僵尸，SDK CloseDevice 未执行 |

### 前端轮询机制

```
用户点击「开始采集」
  → store.start()
  → POST /api/v1/detect/stream/start (CameraController 打开相机)
  → 成功 → isStreaming = true
  → startStreamPolling() → setInterval 2s
  → GET /api/v1/detect/latest?n=5  ← 拉取 raw_url + result_url
  → <img :src="rawUrl"> 渲染
```

**关键**: `isStreaming=true` 是轮询启动的看门狗。外部启动相机不会设这个标志，前端永远不轮询。

### 相机占用诊断

```bash
# 0x80000203 = MV_E_ACCESS_DENIED = 设备已被占用
# 排查:
curl -s http://localhost:8000/api/v1/detect/stream-status | grep active
# active:true 且你未手动启动 → 有残留进程

# 找残留进程:
"A:/Anaconda_envs/envs/ican/python.exe" -c "
import subprocess
r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], capture_output=True, text=True)
for line in r.stdout.split('\n')[3:]:
    parts = line.split()
    if parts and len(parts) > 1 and parts[1].isdigit():
        pid = parts[1]
        r2 = subprocess.run(['C:/Windows/System32/wbem/WMIC.exe', 'process', 'where', f'ProcessId={pid}', 'get', 'CommandLine'], capture_output=True, text=True)
        for l in r2.stdout.strip().split('\n'):
            l = l.strip()
            if l and 'CommandLine' not in l:
                print(f'PID {pid}: {l[:150]}')
"
# 看到 camera_grabber 或 uvicorn 就杀:
# os.kill(pid, signal.SIGTERM)
```

### conda 路径注意

Git Bash 中无法 `conda activate`，始终用完整路径：
```bash
"A:/Anaconda_envs/envs/ican/python.exe"
```
[[conda-bash-path-fix]]

### 相关

- [[demo-workflow-architecture]] — 样机架构、stream_state、端点
- [[project_context]] — 项目状态、权重路径
- [[conda-bash-path-fix]] — bash 中 conda 不可用的根因
