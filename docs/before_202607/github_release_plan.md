# 藻类检测 V2 — GitHub 发布方案

> **状态**: 方案，待审批执行  
> **日期**: 2026-07-05  
> **分支**: `v2-platform`

---

## 一、目标

将 `code/algae_image_v2/` 作为独立可下载的 GitHub 仓库发布，使任意 Windows 用户：

```batch
git clone <repo-url>
cd algae_image_v2
setup.bat    # 一键安装环境
run.bat      # 一键启动
```

---

## 二、文件分类：什么进仓库，什么不进

### 2.1 核心原则

```
┌──────────────────────────────────────────────────┐
│  Git 仓库 = 代码 + 配置 + 前端构建产物             │
│  Git LFS  = 模型权重 (129MB 二进制)                │
│  不入库   = 运行时数据 + conda 环境 + node_modules │
│  GitHub Release = 分发包 (zip，含权重)             │
└──────────────────────────────────────────────────┘
```

### 2.2 逐文件决策表

| 路径 | 大小 | 放哪里 | 原因 |
|------|------|--------|------|
| **代码类** | | | |
| `backend/**/*.py` | ~80KB | Git | 核心代码 |
| `core_engine/**/*.py` | ~35KB | Git | 算法引擎 |
| `shared/*.py` | ~4KB | Git | 共享 schema |
| `desktop_launcher.py` | 1KB | Git | 启动入口 |
| `camera_grabber.py` | ~12KB | Git | 相机采集 |
| `video_grabber.py` | ~4KB | Git | 视频回放 |
| **配置类** | | | |
| `environment.yml` | 2KB | Git | conda 环境定义 |
| `requirements.txt` | 0.2KB | Git | pip 依赖备选 |
| `setup.bat` | 3KB | Git | 一键安装 |
| `run.bat` | 3KB | Git | 一键启动 |
| `AlgaeImageV2.spec` | 1.5KB | Git | PyInstaller 配置 |
| **文档类** | | | |
| `README_install.md` | ~20KB | Git | 安装部署指南 |
| `README.md` | ~4KB | Git | 项目说明 |
| **前端** | | | |
| `frontend/dist/**` | 2.2MB | **Git**（force-add） | 后端直接 serve，用户不需要 Node.js |
| `frontend/src/**` | ~100KB | Git | 源码备份，高级用户可自行改前端 |
| `frontend/package.json` | 0.6KB | Git | npm 依赖声明 |
| `frontend/package-lock.json` | 127KB | Git | 锁定 npm 版本 |
| `frontend/vite.config.js` | 0.5KB | Git | Vite 配置 |
| `frontend/index.html` | 0.3KB | Git | Vite 入口 |
| `frontend/node_modules/` | ~200MB | **不入库** | npm install 即可 |
| **模型权重** | | | |
| `weights/best_v8l.pt` | 83.6MB | **Git LFS** | 核心依赖 |
| `weights/best_v8s.pt` | 21.5MB | **Git LFS** | 核心依赖 |
| `weights/best.pt` | 21.5MB | **Git LFS** | V1 兼容 |
| `weights/rdn_polarization.pth` | 2.4MB | **Git LFS** | 核心依赖 |
| **测试** | | | |
| `tests/**` | ~30KB | Git | 集成测试 |
| `frontend/src/__tests__/**` | ~3KB | Git | 前端测试 |
| **运行时数据** | | | |
| `backend/data/**` | ~1GB | **不入库** | 运行时自动创建 |
| `__pycache__/` | — | **不入库** | Python 缓存 |
| `.pytest_cache/` | — | **不入库** | 测试缓存 |
| **分发** | | | |
| `dist-release_*.zip` | 5.8GB | **不入库** | 改为 GitHub Release 资产 |

---

## 三、.gitignore 设计

需要修改仓库根目录的 `.gitignore`，使 `algae_image_v2/` 下的规则正确：

```gitignore
# ============================================================
# algae_image_v2 专用规则
# ============================================================

# Python
__pycache__/
*.pyc
*.pyo

# 运行时数据（不进仓库，setup.bat 自动创建）
code/algae_image_v2/backend/data/

# Conda 环境（不进仓库，由 environment.yml 重建）
code/algae_image_v2/conda_env/

# 前端依赖（不进仓库，由 npm install 重建）
code/algae_image_v2/frontend/node_modules/

# PyInstaller 构建产物
code/algae_image_v2/dist-release*.zip
code/algae_image_v2/build/
code/algae_image_v2/dist/

# IDE
.vscode/
.idea/

# 临时文件
*.log
session-log.txt
b_err.txt
b_out.txt
build_output.txt

# 但前端 dist/ 要进仓库！（force-add）
# code/algae_image_v2/frontend/dist/  ← 故意不写进 gitignore

# 模型权重由 Git LFS 管理，不在此排除
# *.pt 和 *.pth 已从全局 .gitignore 移除
```

### 3.1 Git LFS 配置

需要为权重文件启用 Git LFS：

```bash
# 在仓库根目录
git lfs track "code/algae_image_v2/weights/*.pt"
git lfs track "code/algae_image_v2/weights/*.pth"

# 生成的 .gitattributes 会自动包含：
# code/algae_image_v2/weights/*.pt filter=lfs diff=lfs merge=lfs -text
# code/algae_image_v2/weights/*.pth filter=lfs diff=lfs merge=lfs -text
```

---

## 四、仓库结构（发布后用户看到的样子）

```
algae_image_v2/                    # 用户 git clone 得到
│
├── README.md                      # 项目简介 + 快速开始
├── README_install.md              # 详细安装部署指南
├── environment.yml                # conda 环境定义
├── requirements.txt               # pip 依赖
├── setup.bat                      # 一键安装
├── run.bat                        # 一键启动（入口）
│
├── desktop_launcher.py            # PyInstaller 入口
├── camera_grabber.py              # 相机采集（可选）
├── video_grabber.py               # 视频回放（可选）
├── AlgaeImageV2.spec              # PyInstaller 打包配置
│
├── backend/                       # FastAPI 后端
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── routes.py
│       ├── routes_data.py
│       ├── schemas.py
│       └── services/
│           ├── pipeline.py
│           ├── camera.py
│           ├── video.py
│           └── stream_state.py
│
├── core_engine/                   # 算法引擎（零框架依赖）
│   ├── config.py
│   ├── polarization_sim.py
│   ├── hsv_polarization.py
│   ├── reconstructor.py
│   ├── enhancement.py
│   ├── inference.py
│   └── quality.py
│
├── shared/
│   └── schemas.py
│
├── frontend/                      # Vue 3 前端
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── dist/                      # ← 构建产物（进仓库，用户无需 npm）
│   │   ├── index.html
│   │   └── assets/
│   └── src/                       # ← 源码（备份，高级用户可修改）
│       ├── main.js
│       ├── App.vue
│       ├── api/
│       ├── router/
│       ├── stores/
│       ├── components/
│       └── views/
│
├── weights/                       # 模型权重（Git LFS）
│   ├── best_v8l.pt                # 83.6 MB ← LFS
│   ├── best_v8s.pt                # 21.5 MB ← LFS
│   ├── best.pt                    # 21.5 MB ← LFS
│   └── rdn_polarization.pth       # 2.4 MB  ← LFS
│
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_frontend.py
│   └── test_pipeline.py
│
└── docs/                          # 设计文档（可选）
    ├── V1_design_spec.md
    └── summary_20260524.md
```

**用户 clone 后看不到的**：
- `backend/data/` — 运行时自动创建
- `frontend/node_modules/` — 不需要（dist/ 已构建）
- `__pycache__/` — Python 缓存

---

## 五、执行步骤（共 8 步）

### Step 1：确保前端 dist/ 是最新的

```bash
cd e:/code/algaeimage/code/algae_image_v2/frontend
npm run build
```

目的：确保 `dist/` 目录中的构建产物与当前源码一致。

### Step 2：修改仓库根目录 .gitignore

将 `code/algae_image_v2/` 相关的规则整理为第三部分的格式，关键是：

- **删除** `*.pt` 和 `*.pth` 的全局排除（权重文件需要 Git LFS 追踪）
- **保留** `backend/data/` 的排除（运行时数据）
- **故意不放** `frontend/dist/` 到 gitignore（需要进仓库）

注意：当前仓库根 `.gitignore` 可能已经有 `*.pt`、`*.pth` 的全局排除。需要改为只在非 LFS 目录排除，或者直接删除全局规则改为按目录排除。

### Step 3：配置 Git LFS 并追踪权重

```bash
cd e:/code/algaeimage
git lfs track "code/algae_image_v2/weights/*.pt"
git lfs track "code/algae_image_v2/weights/*.pth"
git add .gitattributes
git commit -m "chore: enable Git LFS for algae_image_v2 model weights"
```

### Step 4：force-add 权重文件和前端 dist/

```bash
cd e:/code/algaeimage

# 权重文件（之前被 *.pt / *.pth 排除）
git add -f code/algae_image_v2/weights/*.pt
git add -f code/algae_image_v2/weights/*.pth

# 前端构建产物（之前可能在 .gitignore 中）
git add -f code/algae_image_v2/frontend/dist/
```

### Step 5：添加所有新文件和修改

```bash
cd e:/code/algaeimage

git add code/algae_image_v2/.gitignore  # 如果创建了项目级 gitignore
git add code/algae_image_v2/environment.yml
git add code/algae_image_v2/setup.bat
git add code/algae_image_v2/run.bat
git add code/algae_image_v2/README_install.md
git add code/algae_image_v2/backend/
git add code/algae_image_v2/core_engine/
git add code/algae_image_v2/shared/
git add code/algae_image_v2/desktop_launcher.py
git add code/algae_image_v2/camera_grabber.py
git add code/algae_image_v2/video_grabber.py
git add code/algae_image_v2/AlgaeImageV2.spec
git add code/algae_image_v2/tests/
git add code/algae_image_v2/frontend/package.json
git add code/algae_image_v2/frontend/package-lock.json
git add code/algae_image_v2/frontend/vite.config.js
git add code/algae_image_v2/frontend/index.html
git add code/algae_image_v2/frontend/src/
```

### Step 6：提交

```bash
git commit -m "release: algae_image_v2 v2.0 portable — conda env + auto-setup

- Add environment.yml for reproducible conda environment
- Add setup.bat (one-click install) and rewritten run.bat (4-level Python detection)
- Auto-detect MVS SDK paths in camera.py and camera_grabber.py
- Add README_install.md with full deployment guide and file manifest
- Include frontend dist/ for zero-Node.js deployment
- Model weights tracked via Git LFS
- Branch: v2-platform"
```

### Step 7：推送到 GitHub

```bash
git push origin v2-platform

# Git LFS 文件会自动推送到 LFS 存储
```

如果遇到 LFS 带宽限制（GitHub 免费 1GB/月），考虑用 GitHub Release 分发权重文件。

### Step 8：（可选）创建 GitHub Release

如果 `git push` 成功且 LFS 文件正常，可以创建 Release：

1. 在 GitHub 上对 `v2-platform` 分支创建 Release
2. Tag: `v2.0.0`
3. Title: `Algae Image V2.0 — 可移植版`
4. 描述指向 `README_install.md` 的安装说明
5. 如果 LFS 有问题，将 `weights/` 打包为 `algae_v2_weights.zip` 作为 Release 资产

---

## 六、用户下载后的体验

```batch
# 1. 克隆（含 LFS 权重）
git clone https://github.com/<user>/<repo>.git
cd <repo>/code/algae_image_v2
# 或：如果仓库根目录就是 algae_image_v2
git clone https://github.com/<user>/algae_image_v2.git
cd algae_image_v2

# 2. 安装 Miniconda（如未安装）
#    下载 https://docs.conda.io/en/latest/miniconda.html
#    安装勾选 "Add to PATH"

# 3. 一键安装 + 启动
setup.bat    # 首次
run.bat      # 每次启动

# 浏览器自动打开 → http://localhost:8000/app/
```

如果 GitHub LFS 带宽不够导致 clone 时权重文件下载失败，备选方案：

```batch
# 1. 正常 clone（跳过 LFS）
GIT_LFS_SKIP_SMUDGE=1 git clone <repo-url>

# 2. 从 GitHub Release 手动下载 weights.zip
#    解压到 algae_image_v2/weights/

# 3. 安装 + 启动
setup.bat
run.bat
```

---

## 七、潜在问题和应对

| 问题 | 概率 | 应对 |
|------|------|------|
| `*.pt` / `*.pth` 全局 gitignore 与 LFS 冲突 | 高 | Step 2 中整理 .gitignore，改为按目录排除 |
| Git LFS 带宽超限（免费 1GB/月） | 中 | 用 GitHub Release 分发权重文件作为备选 |
| `frontend/dist/` 在 .gitignore 中被排除 | 中 | 检查根 `.gitignore`，确认无 `dist/` 规则；force-add |
| `backend/data/` 中有 1GB 历史数据 | 高 | 确保 `.gitignore` 中有 `backend/data/` 排除规则 |
| `node_modules/` 被意外提交 | 低 | `.gitignore` 中已排除，提交前 `git status` 确认 |
| 首次 LFS push 很慢（129MB 上传） | 中 | 正常现象，一次性成本；网速差时分批 push |
| conda 环境 2-3GB 下载对用户网速要求高 | 中 | README 中注明；可后续做 Docker 方案压缩到 ~3GB 镜像 |
| 用户机器无 GPU | 中 | PyTorch 自动回退 CPU 模式，README 注明性能差异 |

---

## 八、是否拆分独立仓库？

**当前仓库结构** (`e:\code\algaeimage`) 是多项目 monorepo，包含 V1、V2、algae_guardian、训练实验等。对于公开发布，有两个选择：

### 选项 A：保持 monorepo，发布子目录（推荐先用这个）

```
https://github.com/<user>/codex
  └── code/algae_image_v2/    ← 用户只关心这个目录
```

- **优点**：维护成本低，不用拆分，内部一致性高
- **缺点**：用户 clone 整个仓库可能很大（即使子目录可以 sparse-checkout）

### 选项 B：拆分独立仓库

```
https://github.com/<user>/algae_image_v2    ← 独立仓库
```

- **优点**：用户 clone 干净，README 直击主题
- **缺点**：需要维护跨仓库的 `shared/schemas.py` 同步，多仓库管理成本

**建议**：先用选项 A 发布。如果用户反馈仓库太大，再拆分。拆分时 `shared/schemas.py` 复制一份到独立仓库即可（该文件极少变动）。

---

## 九、待定事项

1. **仓库名**：确认 GitHub 上的目标 repo 名（当前 remote 指向哪个？）
2. **License**：是否需要添加 LICENSE 文件（MIT / Apache 2.0 / 私有）？
3. **Git LFS 带宽**：确认 GitHub 账号的 LFS 配额（免费版 1GB 存储 + 1GB 带宽/月，超出需付费或改用 Release 分发）
4. **前端 dist/ 维护策略**：`dist/` 进 git 后，每次改前端都要 `npm run build` + 重新 force-add，是否接受？
