# Vue3 + FastAPI 光电竞赛平台 — 技术规格书

日期: 2026-06-08 | 分支: HSV | 项目: algae_image_v2

---

## 1. 目标

为光电竞赛构建一个 Vue3 + FastAPI 的完整软件产品，替代现有原生 HTML/JS 前端。核心要求：

- 管线上每一步（RGB→偏振→Stokes→增强→检测→预警）**可视化展示**
- 完整产品体验：首页、检测、历史、统计四个页面
- 保留 `core_engine/` 零改动，`backend/` 最小改动

## 2. 架构

```
browser (Vue3 SPA, Vite build)
    │  HTTP REST (JSON + base64 images)
FastAPI (backend/, uvicorn)
    │  import
core_engine/ (纯 Python, 不改)
```

- 开发期：Vite dev server (:5173) proxy → FastAPI (:8000)
- 生产期：Vite build 产物放到 `frontend/dist/`，FastAPI 直接 serve 静态文件

## 3. 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | Vue 3 (Composition API) | 中文生态最成熟 |
| 构建 | Vite 5 | 默认选择，零配置 |
| UI 库 | Element Plus | 中文文档最好，组件最全 |
| 图表 | ECharts 5 + vue-echarts | 交互式，支持缩放导出 |
| 路由 | Vue Router 4 | SPA 页面切换 |
| 状态 | Pinia | Vue3 官方推荐 |
| HTTP | axios | 标准选择 |
| 后端 | FastAPI (已有) | 不变 |

## 4. 页面结构（4 页）

### 4.1 首页 `/`

- 系统标题 + 副标题
- 5 步管线流程动画（Element Plus Steps 组件）
- 项目亮点卡片（偏振成像、深度学习、实时预警）
- 快速跳转按钮 → 检测工具

### 4.2 检测工具 `/detect` ⭐ 核心页面

**上半部分：文件上传**
- `el-upload` 拖拽上传，支持单张/批量
- 上传后自动触发检测

**中部：5 步管线可视化**
- 5 列 `el-card` 并排展示中间结果图：
  1. RGB 原图
  2. 偏振模拟 (I0/I45/I90/I135 四通道蒙太奇)
  3. Stokes 参数 (DoLP/AoP 伪彩色)
  4. I_enh v2 增强结果
  5. YOLO 检测结果 (画框原图)
- 每列有步骤编号 + 标题 + 简要说明

**下半部分：检测结果**
- `el-table` 展示：藻种（中英文）、置信度、风险等级（颜色标签）、框坐标
- 统计卡片：总检测数、高危数、Q 分数、处理耗时
- ECharts：风险分布饼图 + 置信度柱状图
- `el-button` 导出报告

### 4.3 历史记录 `/history`

- `el-table` + 分页：时间、文件名、检测数量、风险等级
- 搜索 + 风险等级筛选
- 点击行 → 弹窗查看完整检测详情

### 4.4 数据统计 `/dashboard`

- 统计卡片行：总检测、今日、高危、平均 Q 分、活跃藻种
- ECharts 曲线：检测趋势（日/周）
- ECharts 饼图：藻种分布
- ECharts 柱状图：风险等级分布

## 5. 后端改动

### 5.1 `backend/app/services/pipeline.py` — 新增方法

```python
def run_with_visualization(self, image_path: str) -> dict:
    """与 run() 相同管线，但额外返回每一步中间结果 base64 图"""
```

返回结构：
```json
{
  "steps": [
    {"title": "RGB原图", "image": "data:image/png;base64,...", "description": "..."},
    {"title": "偏振模拟", "image": "...", "description": "I0/I45/I90/I135四通道"},
    {"title": "Stokes参数", "image": "...", "description": "DoLP/AoP伪彩色图"},
    {"title": "I_enh v2增强", "image": "...", "description": "去散射+对比度增强"},
    {"title": "YOLO检测", "image": "...", "description": "分类框选+风险分级"}
  ],
  "detections": [...],
  "q_score": 0.85,
  "processing_time_ms": 1234,
  "model": "v8l"
}
```

### 5.2 `backend/app/routes/detection.py` — 新增路由

- `POST /api/v1/detect/visualize` — 调用 `run_with_visualization()`
- 保留现有 `POST /api/v1/detect` 兼容旧接口
- 历史记录和统计接口不变

### 5.3 `backend/app/main.py` — 生产模式 serve 前端

```python
# 开发时 Vite dev server 自己跑，不需要这段
# 生产时把 Vite build 产物当静态文件 serve
app.mount("/app", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

## 6. 前端项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js          # proxy /api → :8000
└── src/
    ├── App.vue             # 布局壳：顶栏 + 侧栏 + router-view
    ├── main.js             # 入口：createApp, use router/pinia/element-plus/echarts
    ├── router/index.js     # 4 条路由
    ├── api/index.js        # axios 实例 + API 函数封装
    ├── stores/detect.js    # Pinia: 当前检测结果
    ├── views/
    │   ├── HomePage.vue        # 首页
    │   ├── DetectPage.vue      # 检测工具（核心）
    │   ├── HistoryPage.vue     # 历史记录
    │   └── DashboardPage.vue   # 数据统计
    └── components/
        ├── PipelineViz.vue     # 5 步管线可视化组件
        ├── StepCard.vue        # 单步卡片
        ├── StatsCards.vue      # 统计卡片行
        └── ResultTable.vue     # 检测结果表格
```

## 7. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 中间结果传输 | base64 内嵌 JSON | 简单，不需要额外静态文件服务 |
| 批量检测 | 串行调接口 | 单用户演示，不需要并发 |
| 报告导出 | 前端生成 PDF | 用浏览器 `window.print()` 或 jsPDF |
| 历史数据 | 复用现有 SQLite | backend 已有完整 CRUD |
| CSS 方案 | Element Plus 默认 + scoped style | 不引入 Tailwind，减少依赖 |

## 8. 不变的资产

以下文件和目录在本次改动中**完全不动**：

- `core_engine/` 全部文件
- `weights/` 全部文件
- `backend/app/database.py`
- `backend/app/config.py`
- `backend/app/routes/history.py`
- `backend/app/routes/dashboard.py`
- `desktop_launcher.py`
- `run.bat`

## 9. 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `frontend/` (Vue3 项目) | 全量新建，~12 个文件 |
| 修改 | `backend/app/services/pipeline.py` | 加 `run_with_visualization()` |
| 新增 | `backend/app/routes/detection.py` | 加 `/detect/visualize` 路由 |
| 修改 | `backend/app/main.py` | 生产模式 serve `frontend/dist/` |
| 归档 | `frontend/` (旧) | 移到 `frontend_legacy/` 或删除 |
