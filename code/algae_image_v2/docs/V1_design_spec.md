# 藻影卫士 V1.0 产品设计方案

> **版本**: V1.0  
> **日期**: 2026-05-24  
> **定位**: 单机桌面工具 — 偏振显微藻类智能检测系统  
> **核心管线**: RGB显微图像 → 结构张量偏振模拟 → RDN偏振重建 → I_enh v2增强 → YOLOv8s检测  

---

## 目录

1. [产品定位与范围](#一产品定位与范围)
2. [目录结构](#二目录结构)
3. [核心管线架构](#三核心管线架构)
4. [数据流设计](#四数据流设计)
5. [后端API设计](#五后端api设计)
6. [前端界面设计](#六前端界面设计)
7. [一键启动设计](#七一键启动设计)
8. [代码迁移映射表](#八代码迁移映射表)
9. [错误处理与鲁棒性](#九错误处理与鲁棒性)
10. [测试策略](#十测试策略)
11. [实施步骤](#十一实施步骤)

---

## 一、产品定位与范围

### 1.1 产品形态

| 维度 | 决策 |
|------|------|
| 部署方式 | 单机桌面工具，本地浏览器访问 |
| 启动方式 | 双击 `run.bat` 一键启动（自动激活conda环境、启动后端、打开浏览器） |
| 目标用户 | 水质监测实验员、藻类研究人员 |
| 打包方式 | 当前：脚本启动；未来：PyInstaller/Docker |

### 1.2 功能范围

| 功能模块 | V1 范围 | 说明 |
|----------|---------|------|
| 单图检测 | ✅ 核心功能 | 上传→管线处理→检测结果（框+分类+风险等级） |
| 批量处理 | ✅ 核心功能 | 选择文件夹→批量跑管线→集中查看结果 |
| 检测历史 | ✅ 标准功能 | SQLite存储历史记录，支持查看/删除/导出 |
| 简易仪表板 | ✅ 标准功能 | 检测总数、藻类分布、风险统计图表 |
| 设备管理 | ⚫ 静态占位 | 前端保留页面，不接后端API |
| 人工复核 | ⚫ 静态占位 | 前端保留页面，不接后端API |
| 用户登录 | ❌ 不含 | 单机工具无需多用户 |

### 1.3 技术选型

| 层面 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI (Python) | 已有代码基础，异步支持，自动生成API文档 |
| 数据库 | SQLite + aiosqlite | 单机部署，零配置 |
| 前端 | 原生 HTML/CSS/JS | 无框架依赖，减少打包复杂度 |
| 深度学习 | PyTorch + Ultralytics YOLO | 已有训练权重 |
| 偏振模拟 | 结构张量梯度法 | mAP50=84.7%，物理机理契合暗场显微 |

---

## 二、目录结构

```
algae_image_v1/
├── run.bat                      # 一键启动脚本 (Windows)
├── requirements.txt             # Python依赖
│
├── backend/                     # FastAPI 后端
│   └── app/
│       ├── __init__.py
│       ├── main.py              # 应用入口：挂载静态文件、注册路由、启动事件
│       ├── config.py            # 配置常量（端口8000、路径、模型名、风险阈值）
│       ├── database.py          # SQLite 初始化 + 连接管理 (aiosqlite)
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── detection.py     # POST /api/v1/detect (单图)
│       │   │                    # POST /api/v1/detect/batch (批量)
│       │   ├── dashboard.py     # GET /api/v1/dashboard/stats
│       │   └── history.py       # GET/POST/DELETE /api/v1/history
│       ├── services/
│       │   ├── __init__.py
│       │   └── pipeline.py      # 管线编排器：run_pipeline(image_path) -> result
│       └── schemas.py           # Pydantic 模型定义
│
├── core_engine/                 # 核心管线引擎（纯Python库，零框架依赖）
│   ├── __init__.py
│   ├── polarization_sim.py      # 结构张量偏振模拟：RGB → (I0,I45,I90,I135)
│   ├── reconstructor.py         # RDN 残差稠密网络：4ch noisy → 4ch clean
│   ├── enhancement.py           # I_enh v2 去散射增强公式
│   ├── inference.py             # YOLOv8s 检测封装：图像 → 检测框+类别+置信度
│   ├── quality.py               # Q 质量评分
│   └── config.py                # 藻种定义(95类，来自LifeWatch)、风险阈值、FOV参数
│
├── frontend/                    # 前端静态资源
│   ├── index.html               # SPA 主页面（检测/历史/仪表板 三个Tab）
│   ├── css/
│   │   └── style.css            # 全局样式
│   └── js/
│       ├── app.js               # 主逻辑：Tab切换、API调用、图表渲染
│       ├── detection.js         # 检测模块：上传、预览、结果渲染
│       └── dashboard.js         # 仪表板：Chart.js 统计图表
│
├── weights/                     # 模型权重（不纳入git）
│   ├── rdn_polarization.pth     # RDN偏振重建 (PSNR 62.46dB, 2.5MB)
│   └── best.pt                  # YOLOv8s LifeWatch 95类 (mAP50 84.7%, 22MB)
│
└── docs/                        # 文档
    ├── summary_20260524.md      # 训练总结
    └── V1_design_spec.md        # 本设计文档
```

### 设计原则

1. **core_engine 零框架依赖** — 不 import FastAPI/数据库，纯 numpy/PyTorch，未来可直接被 PyInstaller 或 C++ 调用
2. **backend 薄层** — 只做路由、参数校验、持久化，业务逻辑委托给 core_engine
3. **前端无构建工具** — 原生 ES6 + fetch API，浏览器直接运行，无需 npm/webpack

---

## 三、核心管线架构

### 3.1 管线流程（不可变更顺序）

```
┌──────────┐    ┌─────────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ RGB原图   │───▶│ 结构张量偏振模拟  │───▶│ RDN偏振重建   │───▶│ I_enh v2增强  │───▶│ YOLOv8s检测  │
│ (H×W×3)  │    │ → 4通道(I0,I45,  │    │ 4ch→4ch去噪   │    │ 物理去散射     │    │ 95类目标检测  │
│          │    │   I90,I135)      │    │               │    │               │    │              │
└──────────┘    └─────────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                                     │
                                                                                     ▼
                                                                            ┌──────────────────┐
                                                                            │ 检测结果输出      │
                                                                            │ 框+类别+置信度+    │
                                                                            │ 风险等级+Q评分     │
                                                                            └──────────────────┘
```

### 3.2 各模块详解

#### 阶段1: 结构张量偏振模拟 (`polarization_sim.py`)

- **输入**: RGB 显微图像 (H×W×3, uint8)
- **输出**: 四通道偏振强度 (I₀, I₄₅, I₉₀, I₁₃₅)，shape (4, H, W)
- **物理原理**: 
  - 使用结构张量分析图像局部梯度方向和强度
  - 基于 Malus 定律对每个像素的局部方向计算偏振响应
  - 四个通道全部独立计算，保证 Stokes 参数 S₂ = I₄₅ - I₁₃₅ 的物理意义
- **关键实现**: I₁₃₅ 不是 I₀/I₉₀ 的平均值，而是独立物理模拟

#### 阶段2: RDN 偏振重建 (`reconstructor.py`)

- **输入**: 含噪四通道偏振 (4, H, W)
- **输出**: 去噪重建四通道偏振 (4, H, W)
- **网络**: RDN (Residual Dense Network)
  - 输入4ch → 特征16ch → 12个残差稠密块(每块6层卷积) → 输出4ch
  - 模型大小: ~2.5MB
- **性能**: PSNR 62.46dB (epoch 97, FMPD数据集)
- **作用**: 去除偏振模拟噪声，保持偏振物理一致性（Stokes参数保真）

#### 阶段3: I_enh v2 去散射增强 (`enhancement.py`)

- **输入**: 重建后四通道偏振 → 先计算 Stokes 参数
  - S₀ = I₀ + I₉₀ (总强度)
  - S₁ = I₀ - I₉₀ (水平/垂直差异)
  - S₂ = I₄₅ - I₁₃₅ (对角差异)
  - DoLP = √(S₁² + S₂²) / S₀ (偏振度)
  - AoP = ½·arctan(S₂/S₁) (偏振角)
- **输出**: I_enh 增强图像 (单通道灰度)
- **公式**: `I_enh = Norm(S₀ × (1 + α - γ·DoLP + β·|sin(2·AoP)|·DoLP))`
- **参数**: α=0.6, β=0.25, γ=0.35
- **效果**: 去散射减法模式，高亮细胞壁边缘，压制背景

#### 阶段4: YOLOv8s 检测 (`inference.py`)

- **输入**: I_enh 增强图像 (归一化三通道, 320×320)
- **输出**: 检测框列表 [{bbox, class_id, class_name, confidence}]
- **模型**: YOLOv8s (11.2M参数), LifeWatch 95类训练
- **性能**: mAP50 = 84.7% (13,037张验证集，严格数据隔离)
- **后处理**: 
  - 置信度阈值过滤 (默认 conf≥0.25)
  - NMS 去重 (IoU≥0.7)
  - 风险等级映射 (根据 config.py 中藻种→风险等级)

#### 阶段5: 结果封装

- 将检测结果与原始图像叠加绘制检测框
- 计算 Q 质量评分 (基于DoLP对比度、信噪比)
- 映射风险等级: 高危(产毒蓝藻) / 中危(水华指示种) / 低危(普通藻)

---

## 四、数据流设计

### 4.1 单图检测流程

```
[用户] → 浏览器选择图片
         │
         ▼
    POST /api/v1/detect  (multipart/form-data, image file)
         │
         ▼
    [backend/routes/detection.py]
         │  1. 保存上传文件到 uploads/{uuid}.png
         │  2. 调用 pipeline.run_pipeline(image_path)
         ▼
    [backend/services/pipeline.py]
         │  1. cv2.imread → RGB array
         │  2. core_engine.polarization_sim.simulate(rgb) → I_channels(4,H,W)
         │  3. core_engine.reconstructor.reconstruct(I_channels) → I_clean(4,H,W)
         │  4. core_engine.enhancement.enhance(I_clean) → I_enh(H,W)
         │  5. core_engine.inference.detect(I_enh) → detections[]
         │  6. core_engine.quality.score(I_clean, detections) → q_score
         │  7. 绘制检测框 + 保存结果图到 results/{uuid}.png
         ▼
    [返回 JSON]
         │  { id, detections, q_score, result_image_url, timestamp }
         ▼
    [数据库] → 写入 history 表
         │
         ▼
    [前端] → 显示结果图 + 检测列表 + 风险标签
```

### 4.2 批量检测流程

```
[用户] → 选择文件夹 (含 N 张图片)
         │
         ▼
    POST /api/v1/detect/batch  (multipart, N files)
         │
         ▼
    [后端] → 对每张图顺序执行管线 (未来可并行)
         │  → 收集所有结果
         ▼
    [返回 JSON]
         │  { batch_id, total, results: [{filename, detections, ...}], summary }
         ▼
    [前端] → 批量结果一览表 + 点击展开单图详情
```

### 4.3 数据库表设计 (SQLite)

```sql
-- 检测历史记录
CREATE TABLE detection_history (
    id          TEXT PRIMARY KEY,        -- UUID
    filename    TEXT NOT NULL,           -- 原始文件名
    image_path  TEXT NOT NULL,           -- uploads/{id}.png
    result_path TEXT NOT NULL,           -- results/{id}.png
    detections  TEXT NOT NULL,           -- JSON: [{class, conf, bbox}]
    q_score     REAL,                    -- 质量评分
    risk_level  TEXT,                    -- 'high' / 'medium' / 'low'
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 批量任务
CREATE TABLE batch_tasks (
    id          TEXT PRIMARY KEY,
    total       INTEGER NOT NULL,
    completed   INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'processing',  -- 'processing' / 'done' / 'error'
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 五、后端API设计

### 5.1 检测接口

#### `POST /api/v1/detect` — 单图检测

```
Request:  multipart/form-data { file: <image> }
Response: {
    "id": "uuid",
    "filename": "sample.tif",
    "detections": [
        {
            "class_id": 12,
            "class_name": "Woronichinia",
            "confidence": 0.893,
            "bbox": [x1, y1, x2, y2],
            "risk_level": "high"
        },
        ...
    ],
    "q_score": 0.87,
    "result_image_url": "/static/results/uuid.png",
    "processing_time_ms": 245
}
```

#### `POST /api/v1/detect/batch` — 批量检测

```
Request:  multipart/form-data { files: [<image1>, <image2>, ...] }
Response: {
    "batch_id": "uuid",
    "total": 10,
    "results": [ { "filename": "...", "detections": [...], "status": "ok" }, ... ],
    "summary": {
        "total_detections": 45,
        "high_risk_count": 3,
        "avg_q_score": 0.82
    }
}
```

### 5.2 仪表板接口

#### `GET /api/v1/dashboard/stats`

```
Response: {
    "total_detections": 156,
    "today_count": 12,
    "class_distribution": {
        "Woronichinia": 34, "Spiroides": 28, "Dinobryon": 22, ...
    },
    "risk_distribution": { "high": 15, "medium": 42, "low": 99 },
    "recent_detections": [ ... ]  // 最近10条
}
```

### 5.3 历史记录接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/history?page=1&limit=20` | 分页查询历史 |
| GET | `/api/v1/history/{id}` | 单条详情 |
| DELETE | `/api/v1/history/{id}` | 删除记录 |

### 5.4 静态文件挂载

| URL路径 | 物理路径 | 说明 |
|---------|----------|------|
| `/app/` | `frontend/index.html` | 主界面 |
| `/static/results/` | `backend/data/results/` | 检测结果图 |
| `/static/uploads/` | `backend/data/uploads/` | 上传原图 |

---

## 六、前端界面设计

### 6.1 页面布局

```
┌──────────────────────────────────────────────────────┐
│  藻影卫士 V1.0           [检测] [历史] [仪表板] [设备] [复核] │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ 检测 Tab ─────────────────────────────────────┐  │
│  │                                                  │  │
│  │  ┌─────────────┐   ┌─────────────┐              │  │
│  │  │  拖拽或点击   │   │  检测结果    │              │  │
│  │  │  上传图像     │   │  带框+标签   │              │  │
│  │  │              │   │             │              │  │
│  │  │  [单图检测]   │   │  检测列表:   │              │  │
│  │  │  [批量处理]   │   │  • 沃氏藻    │              │  │
│  │  │              │   │  • 螺旋藻    │              │  │
│  │  └─────────────┘   └─────────────┘              │  │
│  │                                                  │  │
│  │  风险等级: [高危 🔴]  质量评分: 0.87             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ 历史 Tab ─────────────────────────────────────┐  │
│  │  表格: 时间 | 文件名 | 检测数 | 风险 | 操作      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ 仪表板 Tab ───────────────────────────────────┐  │
│  │  统计卡片: 总检测 | 今日 | 高危                │  │
│  │  藻类分布饼图  |  风险柱状图  |  检测趋势折线    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 6.2 交互设计

**检测Tab:**
- 左侧: 拖拽上传区 + "选择文件"按钮 + "批量处理"按钮
- 右侧: 结果展示区（检测框绘制在原图上）+ 检测列表（类别、置信度、风险标签）
- 底部: 风险等级标签（颜色编码: 红/黄/绿）+ Q质量评分 + 处理耗时
- 批量模式: 文件夹选择 → 进度条 → 结果一览表（缩略图+概要）

**历史Tab:**
- 可翻页表格: 时间、文件名、检测到的藻类数、最高风险等级
- 每条可展开查看详细结果图
- 支持删除单条记录

**仪表板Tab:**
- 顶部: 3个统计卡片（总检测次数、今日检测、高危预警数）
- 中部: 藻类分布饼图 + 风险等级柱状图
- 底部: 近7天检测趋势折线图
- 使用 Chart.js CDN（离线时降级为纯文本统计）

### 6.3 静态占位页面

顶部导航栏显示5个Tab：`[检测] [历史] [仪表板] [设备] [复核]`

- **设备管理 Tab**: 点击后显示占位内容 — "设备管理模块将在后续版本开放，敬请期待"
- **人工复核 Tab**: 点击后显示占位内容 — "人工复核模块将在后续版本开放，敬请期待"
- 两个占位Tab保留完整UI框架（导航+标题），仅内容区显示占位提示
- 目的：向甲方展示完整产品蓝图，同时明确当前版本边界

---

## 七、一键启动设计

### 7.1 `run.bat` (Windows)

```batch
@echo off
title 藻影卫士 V1.0
echo ============================================
echo   藻影卫士 - Algae Guardian V1.0
echo   偏振显微藻类智能检测系统
echo ============================================
echo.
echo [1/3] 激活 Conda 环境...
call conda activate ican
echo [2/3] 检查模型权重...
IF NOT EXIST "weights\best.pt" (
    echo [错误] 未找到 YOLO 权重文件 weights\best.pt
    pause
    exit /b 1
)
echo [3/3] 启动后端服务...
start "" http://localhost:8000/app/
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
pause
```

### 7.2 启动时自动执行

1. **环境检查**: 验证 conda 环境 ican 存在
2. **权重校验**: 检查 `weights/rdn_polarization.pth` 和 `weights/best.pt`
3. **目录创建**: 自动创建 `backend/data/uploads/` 和 `backend/data/results/`
4. **模型预加载**: FastAPI startup 事件中加载 RDN + YOLO 模型到内存
5. **浏览器打开**: 自动打开 `http://localhost:8000/app/`

### 7.3 模型加载策略

- **启动时预加载**: 两个模型在 FastAPI `@app.on_event("startup")` 中加载
- **全局单例**: RDN 和 YOLO 模型作为全局变量，所有请求共享
- **内存占用**: RDN ~10MB + YOLO ~90MB ≈ 100MB GPU/CPU内存
- **启动耗时**: 首次加载约5-10秒（含权重文件读取+模型初始化）

---

## 八、代码迁移映射表

### 8.1 core_engine 迁移

| 目标文件 | 源文件 | 修改说明 |
|----------|--------|----------|
| `core_engine/polarization_sim.py` | `algae_guardian/image_processing/polarization_sim.py` | 去掉HSV相关函数，仅保留结构张量法 |
| `core_engine/reconstructor.py` | `algae_guardian/ml/reconstructor.py` | import路径调整，去掉云端路径引用 |
| `core_engine/enhancement.py` | `algae_guardian/image_processing/enhancement.py` | 仅保留I_enh v2公式，去掉v1 |
| `core_engine/inference.py` | `algae_guardian/ml/inference.py` | 适配95类输出，简化接口 |
| `core_engine/quality.py` | `algae_guardian/image_processing/quality.py` | 直接迁移，interface不变 |
| `core_engine/config.py` | `algae_guardian/ml/config.py` | 更新为LifeWatch 95类藻种定义 + 风险等级映射表 |

### 8.2 backend 迁移

| 目标文件 | 源文件 | 修改说明 |
|----------|--------|----------|
| `backend/app/main.py` | `algae_guardian/backend/app/main.py` | 去掉旧static路径，挂载新frontend，精简启动逻辑 |
| `backend/app/routes/detection.py` | `algae_guardian/backend/app/routes/detection.py` | 新增batch端点，调用core_engine而非旧ml模块 |
| `backend/app/routes/dashboard.py` | `algae_guardian/backend/app/routes/dashboard.py` | 适配新数据库表结构 |
| `backend/app/database.py` | `algae_guardian/backend/app/database.py` | 更新表结构（简化，去设备/用户表） |

### 8.3 权重文件迁移

| 目标文件 | 源文件 |
|----------|--------|
| `weights/rdn_polarization.pth` | `algae_guardian/ml/models/rdn_polarization.pth` |
| `weights/best.pt` | `results/yolo_results_20260522/yolo_artifacts/weights/best.pt` |

### 8.4 不迁移的内容

| 目录/文件 | 原因 |
|-----------|------|
| `cloud_training/` | 训练已完成，V1不需要云端训练功能 |
| `Polar_sim_0522/` (HSV) | HSV方案已确认终止，代码保留在仓库以备后用 |
| `tests/` 旧测试 | V1新写针对core_engine的测试 |
| `image_processing/polarization.py` | 被 polarization_sim.py 替代 |
| `image_processing/eval_charts.py` | 仅限训练阶段使用 |
| `ml/preprocessing.py` | 数据预处理仅在训练阶段使用 |
| `ml/postprocessing.py` | 合并到 inference.py |
| `ml/tracker.py` | 时间窗追踪暂不在V1中实现 |

---

## 九、错误处理与鲁棒性

### 9.1 管线异常处理

| 异常场景 | 处理策略 |
|----------|----------|
| 图像格式不支持 | 返回 400 + "支持的格式: PNG, JPG, TIF, BMP" |
| 图像尺寸异常 (< 64×64) | 返回 400 + "图像过小，最小支持64×64像素" |
| RDN 推理失败 | 返回 500 + 记录日志，不中断服务 |
| YOLO 检测无结果 | 正常返回，detections=[]，提示"未检测到藻类" |
| 模型未加载 | 启动时检查，未加载则拒绝启动 |

### 9.2 前端容错

- 批量处理中如果某张图失败，跳过并记录到结果中（status: "error"），不中断整批
- 网络断开时，前端显示"后端连接断开"提示
- Chart.js CDN 加载失败时，仪表板降级为纯文本统计数字

### 9.3 日志

```python
# 使用 Python logging，输出到 stdout + 文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend/data/app.log')
    ]
)
```

---

## 十、测试策略

### 10.1 单元测试 (pytest)

| 测试目标 | 测试内容 |
|----------|----------|
| `test_polarization_sim.py` | 输入RGB图像 → 输出四通道shape正确、值域 [0,1] |
| `test_reconstructor.py` | 给定4ch输入 → RDN输出4ch、PSNR可计算 |
| `test_enhancement.py` | 给定4ch偏振 → I_enh输出单通道、值域正常 |
| `test_inference.py` | 给定I_enh → 返回检测列表格式正确 |
| `test_pipeline.py` | 端到端: RGB → 最终检测结果 |

### 10.2 集成测试

- 启动 FastAPI TestClient → 上传测试图片 → 验证返回JSON结构
- 批量检测: 3张图 → 验证batch_id、结果数量

### 10.3 测试数据

- 从 FMPD 数据集选取 5 张代表性图像作为固定测试集
- 存放于 `tests/fixtures/` 目录

---

## 十一、实施步骤

### 第1步: 目录初始化 (0.5h)
- 创建 `algae_image_v1/` 完整目录树
- 创建 `__init__.py` 文件
- 编写 `requirements.txt`

### 第2步: core_engine 迁移 (2h)
- 从 `algae_guardian/` 复制并精简6个核心模块
- 调整所有 import 路径
- 验证每个模块可独立导入

### 第3步: 权重文件就位 (0.5h)
- 复制 RDN 和 YOLO 权重到 `weights/`
- 编写权重校验逻辑

### 第4步: backend 搭建 (3h)
- 编写 `main.py`, `config.py`, `database.py`
- 编写 `pipeline.py` 管线编排器
- 编写 3 个路由模块 (detection, dashboard, history)
- 本地启动验证 `/docs` 可访问

### 第5步: frontend 开发 (3h)
- 编写 `index.html` 主框架（三Tab布局）
- 编写检测模块 JS（上传、结果渲染）
- 编写历史模块 JS（表格、分页）
- 编写仪表板 JS（Chart.js 图表）
- CSS 样式

### 第6步: 启动脚本 + 集成测试 (1h)
- 编写 `run.bat`
- 端到端测试：启动→上传→检测→查看结果
- 修复集成问题

### 第7步: 文档 + 交付 (0.5h)
- 编写 `V1_手册.md`（用户操作指南）
- 最终检查目录完整性

**预估总工时: 10.5小时**

---

> **下一步**: 用户确认本设计方案后，进入详细实施计划（writing-plans），将每个步骤拆解为可执行的具体任务。
