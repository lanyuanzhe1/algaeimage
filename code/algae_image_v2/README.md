# Algae Image V2 — 藻影知微 有害藻华早期预警平台

FMPD 明场显微藻类智能检测系统。基于 HSV 偏振模拟与 YOLO 深度学习，实现 5 类淡水浮游植物的自动识别与风险预警。

## 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.11 (conda 环境 `ican`)
- **GPU**: NVIDIA GPU ≥ 6GB 显存 (推荐)，CPU 可运行但较慢
- **依赖**: PyTorch ≥ 2.0、Ultralytics、FastAPI、OpenCV

## 快速启动

```
双击 run.bat
```

或命令行：

```bash
conda activate ican
cd e:/code/codex/code/algae_image_v2
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

启动后访问：

| 地址 | 功能 |
|------|------|
| `http://localhost:8000/app/` | 前端界面 |
| `http://localhost:8000/docs` | API 文档 (Swagger) |

## 界面导航

- **首页** — 数据概览、快速检测入口
- **检测工具** — 上传图像、单图/批量检测、查看检出结果
- **历史记录** — 查看、搜索、删除历史检测
- **数据统计** — 藻种分布图、风险分布图、检出趋势

## 检测流程

### 单图检测

1. 进入 **检测工具** 页面，上传藻类显微图像（支持 JPG/PNG/TIFF/BMP）
2. 点击 **单图检测**
3. 右侧显示带标注框的结果图像，下方列出检出藻种及置信度

### 批量检测

1. 点击 **选择文件夹** 加载多张图像，或拖拽文件到上传区域
2. 点击 **批量处理**（最多 50 张）
3. 查看整体统计和各文件结果

## 处理管线

```
RGB 原图 → HSV 偏振模拟 → I_enh v2 图像增强 → YOLO 检测 → 风险预警
```

| 步骤 | 说明 |
|------|------|
| HSV 偏振模拟 | 色彩空间映射 H→AoP, S→DoLP, V→S₀，生成 4 通道偏振图像 |
| I_enh v2 增强 | 基于 DoLP 去散射、AoP 结构增强，提升检测对比度 |
| YOLO 检测 | YOLOv8l 深度学习模型，识别并框选藻类目标 |
| 风险预警 | 根据检出藻种判定风险等级（高危/中危/低危） |

## 5 类藻种

| 名称 | 中文 | 风险等级 | 说明 |
|------|------|----------|------|
| Woronichinia | 沃氏藻 | 🔴 高危 | 产毒蓝藻，水华优势种 |
| Spiroides | 螺旋藻 | 🟡 中危 | 潜在水华形成种 |
| Dinobryon | 锥囊藻 | 🟡 中危 | 异味藻，影响水质 |
| Other-phytoplankton | 其他浮游植物 | 🟢 低危 | 常规浮游植物 |
| Non-phytoplankton | 非浮游植物(杂质) | 🟢 低危 | 杂质/碎屑 |

## 模型选择

系统提供两个 YOLO 模型，API 调用时通过 `model` 参数切换：

| 模型 | mAP50 | 说明 |
|------|-------|------|
| v8l (默认) | 42.9% | 80/20 严格划分，真实泛化性能 |
| v8s | 73.9% | train=val 评估，指标偏高 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/detect?model=v8l` | 单图检测 |
| POST | `/api/v1/detect/batch` | 批量检测 (≤50张) |
| GET | `/api/v1/dashboard/stats` | 仪表板统计 |
| GET | `/api/v1/history` | 检测历史 (分页) |
| DELETE | `/api/v1/history/{id}` | 删除记录 |

## 目录结构

```
algae_image_v2/
├── backend/app/          FastAPI 后端 (路由、数据库、管线编排)
├── core_engine/          核心引擎 (偏振模拟、增强、YOLO检测)
├── frontend/             Web 前端 (原生 HTML/CSS/JS)
├── weights/              模型权重 (YOLOv8l + YOLOv8s)
├── tests/                自动化测试
├── run.bat               Windows 一键启动
└── README.md             本文件
```

## 常见问题

**Q: 启动报错 "weights not found"？**
确保 `weights/best_v8l.pt` 和 `weights/best_v8s.pt` 存在。从 `algae_guardian/data/` 复制 FMPD 训练好的权重。

**Q: 检测速度慢？**
默认使用 GPU。若 CPU 运行，每张约 3-5 秒。GPU（RTX 4050+）约 1-2 秒/张。

**Q: 如何更换模型？**
启动时默认加载 v8l。API 调用时传 `?model=v8s` 切换轻量模型。
