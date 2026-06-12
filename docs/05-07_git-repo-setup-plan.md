# Git 仓库设置方案

## 目标

将项目核心代码和数据集纳入 Git 私有仓库（GitHub），使服务器可直接从仓库克隆并运行完整管线。

## 仓库根目录

`e:/code/codex/`

## 纳入范围

```
e:/code/codex/
├── .claude/              ✅ Claude Code 配置
├── .vscode/              ✅ IDE 配置
├── CLAUDE.md             ✅ 项目指令文件
├── code/algae_guardian/  ✅ 核心项目（含 data/ 全部数据集）
├── docs/                 ✅ 技术文档
│
├── code/SPDRDN/          ❌ 已有独立 git，参考项目
├── pic/                  ❌ 平台展示图片（82MB，非运行必需）
├── 项目文书/             ❌ 光电竞赛文书
├── 参考/                 ❌ 参考资料
├── render_market_survey_0508/ ❌ 市场调研文档
├── video/                ❌ 视频素材
├── algae_guardian_platform.html ❌ 旧版平台页面
├── session-log.txt       ❌ 临时日志
├── tmp_download_fmpd.py  ❌ 临时下载脚本
├── .conda/               ❌ 本地 conda 环境
└── .obsidian/            ❌ 个人笔记配置
```

## .gitignore 规则

### Python 编译产物
```
__pycache__/
*.pyc
*.pyo
*.egg-info/
```

### 运行时生成数据
```
backend/data/results/
backend/data/uploads/
backend/data/reviewed/
backend/data/training_pool/
```

### 冗余备份
```
data/rdn_output_v2_灰度备份/
```

### 临时文件
```
session-log.txt
*.log
~$*
```

### 系统文件
```
.DS_Store
Thumbs.db
```

## Git LFS 配置

### 追踪规则 (`.gitattributes`)

```
*.tif filter=lfs diff=lfs merge=lfs -text
*.tiff filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
*.pth filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
*.npz filter=lfs diff=lfs merge=lfs -text
*.mp4 filter=lfs diff=lfs merge=lfs -text
```

### LFS 追踪的大文件清单

| 路径 | 大小 | 内容 |
|---|---|---|
| `data/download/` | ~12GB | 原始 TIFF 显微图像 (FMPD 数据集) |
| `data/rdn_output_v2/` | ~3.6GB | RDN 偏振重建输出 v2 |
| `data/rdn_training/` | ~694MB | RDN 训练数据 |
| `data/Flowcam_images_training_split_metadata.zip` | ~582MB | 训练集划分压缩包 |
| `data/fmpd_rdn_output/` | ~304MB | RDN 输出 v1（含 labels、train/val 划分） |
| `data/yolo_results/` | ~106MB | YOLO 检测结果 |
| `ml/models/*.pt` | ~93MB | YOLO 模型权重 |
| `ml/models/*.pth` | ~2.5MB | RDN 模型权重 |

## 数据量估算

| 类别 | 大小 |
|---|---|
| 代码 + 文档 | ~1MB |
| data/（除 download 外） | ~5GB |
| data/download/（原始 TIFF） | ~12GB |
| ml/models/ | ~93MB |
| **合计** | **~17GB** |

## GitHub LFS 存储方案

GitHub LFS 免费额度：1GB 存储 + 1GB 带宽/月。

本项目需要 **GitHub Data Plan**：
- $5/月 = 50GB 存储 + 50GB 带宽/月
- 足够覆盖当前 ~17GB 数据集

## 操作步骤

1. 创建 `.gitignore` 文件，排除不需要的文件/目录
2. 创建 `.gitattributes` 文件，配置 LFS 追踪规则
3. `git init` 初始化仓库
4. `git lfs install` 安装 Git LFS
5. `git add .` 暂存所有文件（LFS 自动拦截大文件）
6. `git commit -m "Initial commit: 藻影卫士核心项目 + 完整数据集"`
7. 在 GitHub 创建私有仓库
8. `git remote add origin <私有仓库URL>`
9. `git push -u origin main`
10. 在服务器上 `git clone` 即可获取完整项目

## 服务器克隆后操作

```bash
git clone <私有仓库URL>
cd codex
git lfs pull    # 下载 LFS 大文件
cd code/algae_guardian
conda activate ican
pip install -r requirements.txt
python run.py
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
