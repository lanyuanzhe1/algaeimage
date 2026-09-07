# V2 exe 封装设计

日期: 2026-05-28
范围: `code/algae_image_v2/` → PyInstaller `--onedir` Windows exe

## 决策记录

- **工具**: PyInstaller `--onedir`（非 Nuitka、非 `--onefile`）
- **原因**: PyTorch + ultralytics + opencv 组合下 `--onefile` 首次解压慢且杀软误报高；Nuitka 与 torch C 扩展兼容风险大
- **不做**: 模型切换 bug 修复、前端管线文案修改（用户确认当前状态可接受）
- **云部署**: 已完成，不在本次范围

## 改造清单

### 1. Chart.js 本地化

`frontend/index.html` 第 8 行从 `cdn.jsdelivr.net` 加载，exe 离线环境无法访问。

- 下载 `chart.js@4.4.0` UMD 构建到 `frontend/vendor/chart.umd.min.js`
- 将 `<script src="https://cdn.jsdelivr.net/...">` 改为 `<script src="vendor/chart.umd.min.js">`

### 2. 路径兼容层 (`resource_path`)

`backend/app/config.py` 使用 `__file__` → `os.path.dirname(...)` → `..` 推导项目根目录。PyInstaller 打包后 `__file__` 在 `sys._MEIPASS` 临时目录内解析，与开发环境路径结构不同。

在 `backend/app/config.py` 中新增:

```python
import sys

def resource_path(relative_path):
    """兼容 PyInstaller frozen 和开发环境的路径解析."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative_path)
```

`BASE_DIR`、`WEIGHTS_DIR`、`YOLO_WEIGHTS` 等改用 `resource_path()` 拼接。

`core_engine/inference.py` 中的权重路径也需要同样改造。

### 3. desktop_launcher.py

替代 `run.bat`，作为 PyInstaller 入口点:

- 调用 `resource_path()` 确保静态文件挂载路径正确
- 启动 uvicorn（`backend.app.main:app`）
- `--host 0.0.0.0 --port 8000`
- 自动打开 `http://127.0.0.1:8000/app/`
- 捕获 Ctrl+C / 窗口关闭信号，优雅退出

### 4. PyInstaller spec

关键配置:

- `datas`: `frontend/` 目录、`weights/` 目录 (仅 `best_v8l.pt` + `best_v8s.pt`)
- `hiddenimports`: `torch`, `ultralytics`, `cv2`, `uvicorn`, `fastapi`, `aiosqlite`, `aiofiles`
- `exe`: console=False (Windows GUI 模式，不弹黑窗)
- 排除不需要的数据: `backend/data/` (首次启动自动创建), `tests/`, `docs/`, `__pycache__/`

### 5. `.gitignore`

追加排除: `dist/`, `build/`, `*.spec`

## 产出物目录结构

```
dist/AlgaeImageV2/
  AlgaeImageV2.exe          # 入口
  frontend/                 # HTML/CSS/JS (含 vendor/)
  weights/                  # best_v8l.pt, best_v8s.pt
  backend/                  # Python 包 (编译后)
  core_engine/              # Python 包 (编译后)
  _internal/                # PyInstaller 运行时 + site-packages
```

## 验收标准

- 在无 conda Python 的 Windows 10/11 机器上双击即可启动
- 首次启动无需联网
- `/app/` 可打开，上传 JPG/PNG/TIF/BMP 可预览
- 单图检测输出中文藻种列表、风险等级、结果图
- 关闭窗口后端口释放
- 发行目录不含训练集、缓存、云服务器凭据

## 不做

- 模型切换 (`?model=v8s`) 运行时生效 — 用户确认暂时不管
- 前端管线文案更新 — 用户确认当前状态可接受
- V2 测试修改 — 用户确认测试已通过
- Nuitka / `--onefile` — 已评估，不适合当前依赖组合
