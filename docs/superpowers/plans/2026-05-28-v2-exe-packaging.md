# V2 exe 封装 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `code/algae_image_v2/` 封装为 PyInstaller `--onedir` Windows exe 发行包

**Architecture:** 新增 `resource_path()` 兼容 PyInstaller `_MEIPASS` 路径，新增 `desktop_launcher.py` 替代 `run.bat` 作为入口点，Chart.js 本地化实现离线可用

**Tech Stack:** PyInstaller, Python 3.11, FastAPI + uvicorn, PyTorch + ultralytics, Chart.js 4.4.0

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `frontend/vendor/chart.umd.min.js` | Chart.js 离线副本 |
| Modify | `frontend/index.html:8` | CDN → 本地路径 |
| Modify | `backend/app/config.py:1-18` | 新增 `resource_path()`, 改造路径常量 |
| Modify | `core_engine/inference.py:147-158` | `load_yolo_by_key` 使用 `resource_path` |
| Modify | `backend/app/main.py:10,69` | `FRONTEND_DIR` 使用 `resource_path` |
| Create | `code/algae_image_v2/desktop_launcher.py` | exe 入口，启动 uvicorn + 打开浏览器 |
| Create | `code/algae_image_v2/AlgaeImageV2.spec` | PyInstaller 配置 |
| Modify | `.gitignore` | 追加 `dist/`, `build/`, `*.spec` |

---

### Task 1: Chart.js 本地化

**Files:**
- Create: `code/algae_image_v2/frontend/vendor/chart.umd.min.js`
- Modify: `code/algae_image_v2/frontend/index.html:8`

- [ ] **Step 1: 下载 Chart.js v4.4.0 UMD 构建**

```bash
mkdir -p e:/code/codex/code/algae_image_v2/frontend/vendor
curl -sL -o e:/code/codex/code/algae_image_v2/frontend/vendor/chart.umd.min.js \
  https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
```

验证: `ls -lh code/algae_image_v2/frontend/vendor/chart.umd.min.js` 约 200KB

- [ ] **Step 2: 修改 HTML 引用**

在 `code/algae_image_v2/frontend/index.html:8`：

```diff
-  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
+  <script src="vendor/chart.umd.min.js"></script>
```

- [ ] **Step 3: 验证**

启动服务，打开 `http://localhost:8000/app/`，切换到"数据统计"页面，确认藻类分布图和风险分布图正常渲染。

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v2/frontend/vendor/ code/algae_image_v2/frontend/index.html
git commit -m "feat: localize Chart.js for offline exe packaging"
```

---

### Task 2: 路径兼容层 — `backend/app/config.py`

**Files:**
- Modify: `code/algae_image_v2/backend/app/config.py`

- [ ] **Step 1: 替换 config.py**

将 `code/algae_image_v2/backend/app/config.py` 完整替换为：

```python
"""Application configuration constants."""
import os
import sys


def resource_path(relative_path: str) -> str:
    """Resolve path compatible with both PyInstaller frozen and dev environments.

    When packaged by PyInstaller, sys._MEIPASS is the temp directory containing
    bundled data files. In dev mode, falls back to the project root derived from
    this file's location.
    """
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative_path)


BASE_DIR = resource_path("")

WEIGHTS_DIR = resource_path("weights")
YOLO_WEIGHTS = resource_path("weights/best_v8l.pt")
YOLO_WEIGHTS_V8S = resource_path("weights/best_v8s.pt")

DATA_DIR = resource_path("backend/data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RESULT_DIR = os.path.join(DATA_DIR, "results")
DB_PATH = os.path.join(DATA_DIR, "history.db")

API_PREFIX = "/api/v1"
HOST = "0.0.0.0"
PORT = 8000
```

注意: `BASE_DIR`、`WEIGHTS_DIR`、`YOLO_WEIGHTS`、`YOLO_WEIGHTS_V8S`、`DATA_DIR` 全部改用 `resource_path()`。`UPLOAD_DIR`、`RESULT_DIR`、`DB_PATH` 继承自 `DATA_DIR`，自动获得兼容。

- [ ] **Step 2: 运行测试验证路径解析**

```bash
cd e:/code/codex/code/algae_image_v2
python -c "from backend.app.config import BASE_DIR, WEIGHTS_DIR, YOLO_WEIGHTS; print('BASE:', BASE_DIR); print('Weights:', WEIGHTS_DIR); print('YOLO:', YOLO_WEIGHTS)"
```

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/backend/app/config.py
git commit -m "feat: add resource_path() for PyInstaller frozen path compatibility"
```

---

### Task 3: 路径兼容层 — `core_engine/inference.py`

**Files:**
- Modify: `code/algae_image_v2/core_engine/inference.py:147-158`

- [ ] **Step 1: 替换 `load_yolo_by_key` 中的路径解析**

在 `code/algae_image_v2/core_engine/inference.py` 中，将第 147-159 行替换为：

```python
# ── Model switching (V2) ────────────────────────────────────────────────

def _resolve_weights_root() -> str:
    """Resolve project root for weight file lookup, compatible with PyInstaller."""
    import sys
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_yolo_by_key(model_key: str = DEFAULT_MODEL, device: str = "cpu") -> "YOLO":
    """Load YOLO model by key from AVAILABLE_MODELS config.

    Resolves weights path relative to project root (compatible with PyInstaller).
    """
    if model_key not in AVAILABLE_MODELS:
        raise ValueError(
            f"Unknown model '{model_key}'. Available: {list(AVAILABLE_MODELS.keys())}"
        )
    cfg = AVAILABLE_MODELS[model_key]
    root = _resolve_weights_root()
    weights_path = os.path.join(root, cfg["weights"])
    return load_yolo(weights_path, device)
```

- [ ] **Step 2: 运行管线测试**

```bash
cd e:/code/codex/code/algae_image_v2
python -m pytest tests/test_pipeline.py -v
```

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/core_engine/inference.py
git commit -m "feat: resolve YOLO weights path via _MEIPASS-compatible helper"
```

---

### Task 4: 路径兼容层 — `backend/app/main.py`

**Files:**
- Modify: `code/algae_image_v2/backend/app/main.py:10,69`

- [ ] **Step 1: 替换 main.py 中的路径推导**

在 `code/algae_image_v2/backend/app/main.py` 中：

**第 10 行** — `_PROJECT_ROOT` 改为:
```python
import sys as _sys
if getattr(_sys, 'frozen', False):
    _PROJECT_ROOT = _sys._MEIPASS
else:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

**第 69 行** — `FRONTEND_DIR` 改为:
```python
if getattr(sys, 'frozen', False):
    FRONTEND_DIR = os.path.join(sys._MEIPASS, "frontend")
else:
    FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
FRONTEND_DIR = os.path.normpath(os.path.abspath(FRONTEND_DIR))
```

注意: `sys` 已在文件顶部 import，第 10 行用的是 `_sys`（避免与已导入的 `sys` 冲突，实际直接复用已有 `sys` 即可）。

更简洁版本 — 第 10 行改为:

```python
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = sys._MEIPASS
```

第 69-70 行改为:

```python
if getattr(sys, 'frozen', False):
    _FRONTEND = os.path.join(sys._MEIPASS, "frontend")
else:
    _FRONTEND = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
FRONTEND_DIR = os.path.normpath(os.path.abspath(_FRONTEND))
```

- [ ] **Step 2: 启动验证**

```bash
cd e:/code/codex/code/algae_image_v2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
sleep 3
curl -s http://localhost:8000/app/ | head -5
```

确认返回 HTML（非 404）。

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/backend/app/main.py
git commit -m "feat: resolve frontend dir via _MEIPASS-compatible path in main.py"
```

---

### Task 5: desktop_launcher.py

**Files:**
- Create: `code/algae_image_v2/desktop_launcher.py`

- [ ] **Step 1: 创建 desktop_launcher.py**

```python
"""Desktop launcher for Algae Image V2 — PyInstaller entry point.

Starts uvicorn, opens the browser, and handles graceful shutdown.
"""
import os
import sys
import threading
import webbrowser


def _open_browser(url: str, delay: float = 2.0):
    """Open browser after a short delay to let uvicorn start."""
    import time
    time.sleep(delay)
    webbrowser.open(url)


def main():
    import uvicorn

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/app/"

    print("=" * 50)
    print("  Algae Image V2")
    print("  FMPD Bright-field Algae Detection")
    print(f"  {url}")
    print("  Press Ctrl+C to exit")
    print("=" * 50)

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 本地验证**

```bash
cd e:/code/codex/code/algae_image_v2
python desktop_launcher.py
```

确认浏览器自动打开，前端页面正常加载，检测功能可用。Ctrl+C 退出。

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/desktop_launcher.py
git commit -m "feat: add desktop_launcher.py as PyInstaller entry point"
```

---

### Task 6: PyInstaller .spec 文件

**Files:**
- Create: `code/algae_image_v2/AlgaeImageV2.spec`

- [ ] **Step 1: 创建 .spec 文件**

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['desktop_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('weights', 'weights'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'fastapi',
        'torch',
        'ultralytics',
        'ultralytics.nn.modules',
        'cv2',
        'numpy',
        'PIL',
        'aiosqlite',
        'aiofiles',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'tkinter',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AlgaeImageV2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AlgaeImageV2',
)
```

关键配置说明:
- `console=False` — Windows GUI 模式，不弹黑窗
- `datas` — 打包 `frontend/` 和 `weights/` 目录
- `hiddenimports` — uvicorn 子模块、torch、ultralytics 等 PyInstaller 无法自动探测的导入
- `excludes` — 排除不用的 pytest、tkinter、unittest 减小体积
- `name='AlgaeImageV2'` — 产物 exe 和目录名

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v2/AlgaeImageV2.spec
git commit -m "feat: add PyInstaller spec for onedir Windows build"
```

---

### Task 7: .gitignore 更新

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 追加构建产物排除**

在 `.gitignore` 末尾追加:

```
# PyInstaller build artifacts
dist/
build/
*.spec
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: exclude PyInstaller build artifacts from git"
```

---

### Task 8: 构建与验收

- [ ] **Step 1: 安装 PyInstaller**

```bash
conda activate ican
pip install pyinstaller
```

- [ ] **Step 2: 构建**

```bash
cd e:/code/codex/code/algae_image_v2
pyinstaller AlgaeImageV2.spec --clean --noconfirm
```

预期产出: `dist/AlgaeImageV2/AlgaeImageV2.exe`

- [ ] **Step 3: 验证产物**

```bash
ls dist/AlgaeImageV2/AlgaeImageV2.exe
ls dist/AlgaeImageV2/frontend/index.html
ls dist/AlgaeImageV2/weights/best_v8l.pt
```

- [ ] **Step 4: 双击启动测试**

在文件管理器中双击 `dist/AlgaeImageV2/AlgaeImageV2.exe`，确认:
- 浏览器自动打开 `http://127.0.0.1:8000/app/`
- 前端页面正常渲染（仪表板图表可见 = Chart.js 本地化成功）
- 上传一张测试图片，检测返回结果
- 关闭窗口，确认浏览器可关，端口释放

### Task 9: 打包分发

- [ ] **Step 1: 压缩发行包**

```bash
cd e:/code/codex/code/algae_image_v2/dist
# Windows: 用 PowerShell Compress-Archive 或右键压缩
powershell -Command "Compress-Archive -Path AlgaeImageV2 -DestinationPath AlgaeImageV2-windows-amd64.zip"
```

验收: zip 可解压到任意路径，双击 exe 可运行，不依赖原始代码目录。

---

*计划结束 — 共 9 个 Task*
