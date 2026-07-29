# V1/V2 封装 exe 与云服务器上线方案

日期: 2026-05-27  
项目根目录: `E:/code/algaeimage`

## 1. 当前工程判断

### 推荐主线

下一步建议以 `code/algae_image_v2/` 作为公网网页上线与 exe 封装主线。

原因:

- V2 面向 FMPD 明场显微图像，页面名称已经是“藻影知微 有害藻华早期预警平台”，更接近当前产品叙事。
- V2 管线更轻: `RGB -> HSV 偏振模拟 -> I_enh v2 增强 -> YOLOv8l -> 5 类输出`，跳过 RDN，速度和部署复杂度都低于 V1。
- V2 已经有 FastAPI 后端、静态前端 `/app/`、Swagger `/docs`、历史记录 SQLite、权重目录和一键启动脚本。
- V2 当前权重齐全: `weights/best_v8l.pt` 约 88 MB，`weights/best_v8s.pt` 约 22 MB。

### V1 定位

`code/algae_image_v1/` 建议保留为稳定演示版 / 论文答辩版 / 离线桌面版候选。

V1 管线:

`RGB -> 结构张量偏振模拟 -> RDN 偏振重建 -> I_enh v2 增强 -> YOLOv8s 95 类`

优势是历史指标强，结构张量 + RDN 路线完整；劣势是面向 95 类 LifeWatch，和 V2 的 FMPD 5 类产品口径不完全一致。

## 2. 上线前必须修正

优先级 P0:

1. 更新 V2 前端管线文案  
   当前 `frontend/index.html` 顶部 pipeline bar 仍写着 V1 的“偏振暗场采集 / Stokes重建 / RDN”等文案。应改为:
   `明场图像上传 -> HSV偏振模拟 -> I_enh增强 -> YOLOv8l检测 -> 风险预警`

2. 修正 V2 核心测试  
   当前 `tests/test_pipeline.py` 仍有 V1 断言，例如 `LIFEWATCH_95_CLASSES`、`Microcystis`、RDN fixture。应改为 FMPD 5 类、HSV 无 RDN、模型选择 `best_v8l.pt/best_v8s.pt`。

3. 修正 `/api/v1/detect?model=v8s` 实际未切换模型的问题  
   当前路由接收 `model` 参数，但调用的是启动时加载好的全局 `pipeline.run(filepath)`。如果需要模型切换，应实现模型 runner 缓存或按参数选择对应 YOLO。

4. 去掉公网依赖 CDN  
   前端使用 Chart.js CDN。exe 离线运行和国内公网访问都可能受影响，应将 Chart.js 下载到 `frontend/vendor/chart.umd.min.js` 并改为本地引用。

5. 敏感信息处理  
   `docs/cloud_training_record_0507.md` 中含云服务器 SSH 连接信息和明文密码。上线或公开仓库前必须删除、替换为占位符，并轮换该密码。

优先级 P1:

- `core_engine/inference.py` 顶部 docstring 仍写“YOLOv8s 95-class”，应改为 V2/FMPD 5-class。
- V2 `docs/` 仍复制了 V1 设计文档，应新增 V2 设计说明，避免交接混乱。
- 前端“设备管理 / 人工复核”为占位页，上线演示可保留，但正式版本应隐藏或标注 beta。
- 打包/部署前清理 `backend/data/history.db` 是否需要随包分发。正式包建议首次启动自动创建空库，不把历史记录打进发行包。

## 3. exe 封装方案

### 推荐路线: PyInstaller onedir

不建议第一版用 `--onefile`。本项目包含 PyTorch、Ultralytics、OpenCV、YOLO 权重和静态前端，`onefile` 首次启动会解压大量文件，杀毒误报和路径问题更多。

推荐用 `onedir` 生成一个发行目录:

```
dist/AlgaeImageV2/
  AlgaeImageV2.exe
  weights/
  frontend/
  backend/data/
  ...
```

用户双击 exe 后:

1. 启动 FastAPI/uvicorn。
2. 自动打开 `http://127.0.0.1:8000/app/`。
3. 程序退出时释放模型。

### 封装改造点

1. 新增 `desktop_launcher.py`
   - 负责启动 uvicorn。
   - 自动打开浏览器。
   - 处理 PyInstaller `_MEIPASS` / frozen 路径。

2. 路径改造
   - `backend/app/config.py` 和 `core_engine/inference.py` 需要统一使用 `resource_path()`。
   - 权重、前端静态资源、数据库目录不能依赖当前工作目录。

3. 依赖锁定
   - 建议新增 `requirements-lock.txt` 或 `environment.yml`。
   - 对 torch/ultralytics/opencv/pydantic 固定版本，避免现场安装漂移。

4. 本地化静态资源
   - Chart.js 改成本地文件。

5. 构建命令雏形

```
pyinstaller desktop_launcher.py ^
  --name AlgaeImageV2 ^
  --onedir ^
  --noconsole ^
  --add-data "frontend;frontend" ^
  --add-data "weights;weights" ^
  --add-data "backend;backend" ^
  --add-data "core_engine;core_engine" ^
  --hidden-import "ultralytics" ^
  --hidden-import "cv2" ^
  --hidden-import "torch"
```

实际项目更适合写成 `AlgaeImageV2.spec`，把 `datas`、`hiddenimports`、权重和前端资源固定下来。

### 验收标准

- 在一台未配置 conda 的 Windows 10/11 机器上可双击启动。
- 首次启动不需要联网。
- `/app/` 可打开，上传 JPG/PNG/TIF/BMP 可预览。
- 单图检测能输出中文藻种列表、风险等级、结果图。
- 关闭窗口或 Ctrl+C 后端口释放。
- 发行目录不包含训练集、缓存、历史图片、旧云服务器凭据。

## 4. 云服务器上线方案

### 推荐架构

```
用户浏览器
  -> HTTPS 域名
  -> Nginx 反向代理
  -> FastAPI/Uvicorn
  -> V2 推理服务 + SQLite
  -> 本地磁盘保存上传图和结果图
```

第一版不需要前后端分离构建。FastAPI 已能同时提供 API 和静态前端。

### 服务器规格建议

演示/低频访问:

- 2 vCPU / 4 GB RAM / 80 GB SSD
- CPU 推理可用但慢，适合评委演示、少量图片上传。

正式演示/多人访问:

- 4 vCPU / 8-16 GB RAM / 100 GB SSD
- NVIDIA T4 / L4 / RTX 系列 GPU 任选其一
- 目标是减少 YOLOv8l 推理延迟，并避免多人上传时阻塞。

成本优先:

- 默认加载 `best_v8s.pt`，保留 `best_v8l.pt` 作为高精度模式。
- 这样可以用 CPU 云主机先上线网页，再决定是否升级 GPU。

### 国内/海外选择

国内云服务器:

- 优点: 国内访问快，适合比赛、学校、展示。
- 注意: 使用中国内地服务器绑定域名通常需要 ICP 备案。备案周期会影响上线时间。

海外云服务器:

- 优点: 可更快用域名上线，通常无 ICP 备案流程。
- 注意: 国内访问速度和稳定性可能不如国内服务器。

临时展示:

- 可以先用服务器公网 IP + 端口，或用 Cloudflare Tunnel / frp 做临时访问。
- 正式展示建议域名 + HTTPS。

### 部署方式

推荐 Docker Compose:

```
services:
  app:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./backend/data:/app/backend/data
      - ./weights:/app/weights:ro
    restart: unless-stopped

  nginx:
    image: nginx:stable
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./deploy/certs:/etc/nginx/certs:ro
    depends_on:
      - app
    restart: unless-stopped
```

如果服务器不用 Docker，也可以用:

- conda/venv 安装依赖
- `systemd` 管理 uvicorn
- Nginx 反代 `127.0.0.1:8000`

### 上线验收标准

- `https://域名/app/` 可访问。
- `https://域名/docs` 可访问或按需关闭。
- 上传、预览、单图检测、历史记录、统计图可用。
- Nginx 限制上传大小，例如 20-50 MB。
- HTTPS 证书自动续期。
- 后台服务重启后自动恢复。
- 上传目录和结果目录有定期清理策略。

## 5. 推荐执行顺序

第一阶段: 1 天内完成本地可交付

1. 修 V2 前端文案和测试。
2. 实现本地 Chart.js。
3. 固定依赖版本。
4. 清理敏感信息。
5. 跑通 `python -m pytest tests/test_frontend.py tests/test_pipeline.py`。

第二阶段: 1-2 天完成 exe 预发行

1. 新增 `desktop_launcher.py`。
2. 写 PyInstaller spec。
3. 产出 `dist/AlgaeImageV2/`。
4. 在干净 Windows 环境试运行。
5. 压缩成 zip 交付包。

第三阶段: 1-2 天完成公网演示版

1. 购买云服务器。
2. 部署 Docker/venv 环境。
3. 上传 V2 项目和权重。
4. 配置 Nginx、HTTPS、域名。
5. 跑一次真实图片检测，截图留档。

第四阶段: 正式版加固

1. 增加登录或上传限流。
2. 增加任务队列，避免多人上传阻塞。
3. 定时清理上传和结果图片。
4. 为历史记录换成 PostgreSQL 或保留 SQLite 但加备份。
5. 增加日志、错误追踪和健康检查。

## 6. 当前结论

最稳妥方案:

- 产品主线: `algae_image_v2`
- exe: PyInstaller `onedir`
- 云上线: Docker Compose + Nginx + HTTPS
- 服务器: 先 CPU 4C8G 上网页，若推理延迟不可接受再换 GPU
- 先修 P0，再打包和上线

## 7. 参考资料

- PyInstaller 官方文档: `--onedir` 是默认的一文件夹发行方式，`--onefile` 是单文件发行方式；官方也建议先让 one-folder 模式正常工作，再尝试 one-file。
- PyInstaller 官方文档: 静态资源、权重等数据文件可通过 `--add-data` 或 `.spec` 文件的 `datas` 加入 bundle。
- 阿里云 ICP 备案说明: 域名解析到中国内地服务器并对外提供 Web 服务时通常需要备案。
- 腾讯云 CVM/GPU 计费文档: 云服务器实例价格包含 CPU/内存、磁盘、网络等部分；GPU 云服务器有包年包月、按量计费、竞价实例等计费模式，实际价格应以购买页/价格计算器为准。
- Cloudflare Tunnel 官方文档: 可将公网 hostname 映射到本地服务，例如 `app.example.com -> http://localhost:8000`，适合临时演示或隐藏源站 IP。
