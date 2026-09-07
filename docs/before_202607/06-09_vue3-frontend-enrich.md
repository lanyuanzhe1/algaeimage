# Vue3 前端丰富化 — 从 Legacy 迁移界面元素

**日期:** 2025-06-09
**分支:** HSV

## 完成事项

- 对比分析 legacy 前端 (`frontend_legacy/index.html`) 与 Vue3 前端的差异，识别 7 项缺失功能
- 新增 3 个可复用组件：MetricsBar、RiskSummary、DataLoop
- 重写 HomePage.vue：从简单落地页改为三栏检测仪表板布局
- 新增 2 个占位页面：DevicesPage、ReviewPage
- 更新 App.vue 导航栏和路由配置
- 构建验证通过，启动 dev server 预览全部 6 个页面
- Git 提交：`663a7db`

## 技术细节

### 新增文件
| 文件 | 说明 |
|------|------|
| `src/components/MetricsBar.vue` | 全局 5 卡片指标栏，调用 `getStats()` API |
| `src/components/RiskSummary.vue` | 四级预警静态面板（纯展示组件） |
| `src/components/DataLoop.vue` | 数据闭环四步可视化静态组件 |
| `src/views/DevicesPage.vue` | 设备管理占位页，设备状态进度条 |
| `src/views/ReviewPage.vue` | 人工复核占位页，复用 DataLoop 组件 |

### 重写文件
- **`src/views/HomePage.vue`**：三栏布局（`el-row` + `el-col`，桌面端 6:12:6），左栏为数据概览+快捷操作+管线缩略图，中栏集成完整检测流程（拖拽上传→进度→PipelineViz→ResultTable→ECharts 风险/置信度图表），右栏为最近检测列表+RiskSummary+DataLoop

### 修改文件
- `src/App.vue`：导航新增"设备管理"`/devices`、"人工复核"`/review`
- `src/router/index.js`：新增 2 条懒加载路由

### 复用策略
- `StatsCards.vue` 被 `MetricsBar` 包裹使用
- `PipelineViz.vue`、`ResultTable.vue` 在 HomePage 中栏直接引用
- `detectVisualize()` 和 `getStats()` API 函数直接引用
- Element Plus 图标已全局注册（`main.js` 第 38-40 行），无需逐个导入

### 构建结果
```
vite v6.4.3 building for production...
✓ 2236 modules transformed in 4.23s
dist/ 产出 HomePage-CiLgOMuE.js (12.21 KB), 新页面各 <2 KB
```

## 遇到的问题

无。构建和预览均一次通过。控制台仅有预期的 500 错误（macOS 未启动 Python 后端），前端组件正确降级显示 `--`。

## 结果/产出

- 6 页面应用：首页(丰富三栏) / 检测工具 / 历史记录 / 数据统计 / 设备管理 / 人工复核
- 构建产物已一并提交到 `dist/`
- Dev server: `http://localhost:5173/`（仍在运行）

## 下一步

当前 legacy 前端还有以下内容未迁移：
- **导出报告 modal**：legacy 有"导出报告"按钮和弹窗，Vue3 尚未实现
- **批次上传检测**：HomePage 有"批量处理"按钮但 `runBatchDetection` 为空函数
- 首页 MetricsBar 与 DashboardPage 各自独立调用 `getStats()`，可考虑共享请求缓存
