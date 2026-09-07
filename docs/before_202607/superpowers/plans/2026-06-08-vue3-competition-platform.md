# Vue3 + FastAPI 光电竞赛平台 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 algae_image_v2 前端用 Vue3 + Element Plus + ECharts 重写，后端新增管线可视化 API，构建光电竞赛演示平台。

**Architecture:** Vue3 SPA (Vite build) 通过 HTTP REST 调用 FastAPI。core_engine/ 零改动，backend/ 新增 `run_with_visualization()` 和 `/detect/visualize` 路由。

**Tech Stack:** Vue3 (Composition API), Vite 5, Element Plus, ECharts 5 + vue-echarts, Vue Router 4, Pinia, axios, FastAPI (已有)

---

## 文件结构

```
code/algae_image_v2/
├── backend/app/
│   ├── routes.py           ← 修改: 新增 /detect/visualize 路由
│   ├── schemas.py          ← 修改: 新增 VizStep, VizDetectResponse
│   ├── main.py             ← 修改: 生产模式 serve frontend/dist
│   └── services/
│       └── pipeline.py     ← 修改: 新增 run_with_visualization()
├── frontend/               ← 全量替换为 Vue3 项目
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/index.js
│       ├── api/index.js
│       ├── stores/detect.js
│       ├── views/
│       │   ├── HomePage.vue
│       │   ├── DetectPage.vue
│       │   ├── HistoryPage.vue
│       │   └── DashboardPage.vue
│       └── components/
│           ├── PipelineViz.vue
│           ├── StepCard.vue
│           ├── StatsCards.vue
│           └── ResultTable.vue
└── frontend_legacy/        ← 旧 frontend/ 归档
```

---

### Task 1: 后端 — pipeline.py 新增 run_with_visualization()

**Files:**
- Modify: `code/algae_image_v2/backend/app/services/pipeline.py`

- [ ] **Step 1: 添加 base64 编码辅助函数和 run_with_visualization 方法**

在 `pipeline.py` 文件末尾（`PipelineRunner` 类内部）新增以下方法。在文件顶部 import 区添加 `import base64` 和 `from core_engine.enhancement import compute_stokes`。

```python
# 在文件顶部 import 区域，第7行后添加:
import base64

# 在现有 import 中，第7行 enhancement 只导入了 enhance，需要加上 compute_stokes:
from core_engine.enhancement import enhance, compute_stokes
```

在 `PipelineRunner` 类的 `_draw_boxes` 方法之后，新增以下方法：

```python
    def run_with_visualization(self, image_path: str) -> dict:
        """Execute V2 pipeline and return every intermediate step as base64 images.

        Pipeline: RGB → HSV polarization → Stokes params → I_enh v2 → YOLO

        Returns dict with:
            steps: list of {title, image (base64 data-URI), description}
            detections, q_score, processing_time_ms, model
        """
        import time
        t0 = time.time()

        rgb = cv2.imread(image_path)
        if rgb is None:
            raise ValueError(f"Cannot read image: {image_path}")
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        def _rgb_to_b64(img_rgb: np.ndarray) -> str:
            """Convert RGB ndarray to base64 data-URI PNG."""
            _, buf = cv2.imencode(".png", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            return "data:image/png;base64," + base64.b64encode(buf).decode()

        def _gray_to_b64(img_gray: np.ndarray) -> str:
            """Convert grayscale ndarray [0,1] to base64 data-URI PNG."""
            vis = np.clip(img_gray * 255, 0, 255).astype(np.uint8)
            _, buf = cv2.imencode(".png", vis)
            return "data:image/png;base64," + base64.b64encode(buf).decode()

        # Step 1: HSV polarization simulation → 4-channel
        I_channels = simulate_polarization(rgb)

        # Build polarization montage: tile I0, I45, I90, I135
        h, w = rgb.shape[:2]
        pol_montage = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
        angle_labels = ["I0 (0°)", "I45 (45°)", "I90 (90°)", "I135 (135°)"]
        for idx in range(4):
            row, col = idx // 2, idx % 2
            ch = np.clip(I_channels[idx] * 255, 0, 255).astype(np.uint8)
            ch_rgb = cv2.cvtColor(ch, cv2.COLOR_GRAY2RGB)
            cv2.putText(ch_rgb, angle_labels[idx], (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            pol_montage[row*h:(row+1)*h, col*w:(col+1)*w] = ch_rgb

        # Step 2: Stokes parameters (DoLP + AoP as color-mapped images)
        stokes = compute_stokes(I_channels)
        DoLP = stokes["DoLP"]
        AoP = stokes["AoP"]

        # DoLP as heatmap (grayscale, DoLP in [0,1])
        DoLP_vis = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
        DoLP_rgb = cv2.applyColorMap(DoLP_vis, cv2.COLORMAP_MAGMA)
        cv2.putText(DoLP_rgb, "DoLP (偏振度)", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # AoP as HSV colormap (AoP in [-π/2, π/2] → map to [0, 180] hue)
        AoP_norm = ((AoP + np.pi / 2) / np.pi * 180).astype(np.uint8)
        AoP_hsv = np.zeros((h, w, 3), dtype=np.uint8)
        AoP_hsv[:, :, 0] = AoP_norm
        AoP_hsv[:, :, 1] = 200
        AoP_hsv[:, :, 2] = np.clip(DoLP * 255, 50, 255).astype(np.uint8)
        AoP_rgb = cv2.cvtColor(AoP_hsv, cv2.COLOR_HSV2RGB)
        cv2.putText(AoP_rgb, "AoP (偏振角)", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Stokes montage: DoLP left, AoP right
        stokes_montage = np.hstack([DoLP_rgb, AoP_rgb])

        # Step 3: I_enh v2 enhancement
        I_enh = enhance(I_channels, alpha=IENH_ALPHA, beta=IENH_BETA, gamma=IENH_GAMMA)

        # Step 4: YOLO detection
        detections = detect(self.yolo, I_enh)

        # Step 5: Draw boxes
        result_img = self._draw_boxes(rgb, detections)

        # Q score
        q_score = compute_q_score(I_channels)

        elapsed_ms = (time.time() - t0) * 1000

        return {
            "steps": [
                {
                    "title": "1. RGB原图",
                    "image": _rgb_to_b64(rgb),
                    "description": f"明场显微图像 ({w}×{h})",
                },
                {
                    "title": "2. 偏振模拟",
                    "image": _rgb_to_b64(pol_montage),
                    "description": "HSV色彩空间法 → I0/I45/I90/I135 四通道",
                },
                {
                    "title": "3. Stokes参数",
                    "image": _rgb_to_b64(stokes_montage),
                    "description": "DoLP偏振度 + AoP偏振角 伪彩色图",
                },
                {
                    "title": "4. I_enh v2增强",
                    "image": _gray_to_b64(I_enh),
                    "description": "S0(1+α-γ·DoLP+β·|sin(2·AoP)|·DoLP)",
                },
                {
                    "title": "5. YOLO检测",
                    "image": _rgb_to_b64(result_img),
                    "description": f"{len(detections)} 个检测 · 风险分级标注",
                },
            ],
            "detections": detections,
            "q_score": float(q_score),
            "processing_time_ms": elapsed_ms,
            "model": self.model_key,
        }
```

- [ ] **Step 2: 验证 pipeline.py 语法正确**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2
python -c "from backend.app.services.pipeline import PipelineRunner; print('OK')"
```

---

### Task 2: 后端 — schemas.py 新增可视化响应模型

**Files:**
- Modify: `code/algae_image_v2/backend/app/schemas.py`

- [ ] **Step 1: 在 schemas.py 末尾追加新的 Pydantic 模型**

在 `schemas.py` 文件末尾（第74行后）追加：

```python
class VizStep(BaseModel):
    """One intermediate pipeline step with base64 image."""
    title: str
    image: str              # data:image/png;base64,...
    description: str


class VizDetectResponse(BaseModel):
    """Response for POST /api/v1/detect/visualize — includes all pipeline steps."""
    id: str
    filename: str
    steps: list[VizStep]
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    processing_time_ms: float
```

- [ ] **Step 2: 验证 schemas.py 语法正确**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2
python -c "from backend.app.schemas import VizStep, VizDetectResponse; print('OK')"
```

---

### Task 3: 后端 — routes.py 新增 /detect/visualize 路由

**Files:**
- Modify: `code/algae_image_v2/backend/app/routes.py`

- [ ] **Step 1: 在 schemas import 中加入新模型**

在第19行 `from .schemas import (` 块中追加 `VizStep, VizDetectResponse`：

```python
from .schemas import (
    BatchDetectResponse,
    BatchResult,
    BatchSummary,
    DetectionItem,
    HistoryItem,
    HistoryListResponse,
    SingleDetectResponse,
    StatsResponse,
    VizStep,              # 新增
    VizDetectResponse,     # 新增
)
```

- [ ] **Step 2: 在 /detect/batch 路由之后（第208行后）新增 /detect/visualize 路由**

```python
@router.post("/detect/visualize", response_model=VizDetectResponse)
async def detect_visualize(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Upload a single micrograph and run detection WITH intermediate pipeline visualization."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, TIF, BMP)")

    file_id, filepath = await _save_upload(file)

    try:
        result = pipeline.run_with_visualization(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    det_items = _to_detection_items(result["detections"])
    risk = _overall_risk(result["detections"])

    # Save result image (last step) for history
    result_url = await _save_result(file_id, result["detections"])

    await db.execute(
        """INSERT INTO detection_history
               (id, filename, image_path, result_path, detections, q_score, risk_level)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            file_id,
            file.filename or "unknown",
            filepath,
            result_url,
            json.dumps([d.model_dump() for d in det_items]),
            round(result["q_score"], 4),
            risk,
        ),
    )
    await db.commit()

    return VizDetectResponse(
        id=file_id,
        filename=file.filename or "unknown",
        steps=[VizStep(**s) for s in result["steps"]],
        detections=det_items,
        q_score=round(result["q_score"], 4),
        risk_level=risk,
        processing_time_ms=round(result["processing_time_ms"], 1),
    )
```

- [ ] **Step 3: 验证路由正确注册**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2
python -c "
from backend.app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print([r for r in routes if 'visualize' in r])
"
```

---

### Task 4: 前端 — Vue3 + Vite 脚手架

**Files:**
- Create: `code/algae_image_v2/frontend/` (整个项目)

- [ ] **Step 1: 归档旧 frontend**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2
mv frontend frontend_legacy
```

- [ ] **Step 2: 使用 npm create vue 脚手架**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2
npm create vue@latest frontend -- --router --pinia --vue-router --pinia
```

执行过程中选择：
- Project name: `frontend`
- TypeScript: No
- JSX: No
- Vue Router: Yes
- Pinia: Yes
- Vitest: No
- ESLint: No
- DevTools: No

- [ ] **Step 3: 安装 Element Plus 和 ECharts**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2/frontend
npm install element-plus @element-plus/icons-vue echarts vue-echarts axios
```

- [ ] **Step 4: 验证脚手架能启动**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2/frontend
npm run dev
```

Expected: Vite dev server 在 `http://localhost:5173` 启动，显示 Vue3 默认欢迎页面。

---

### Task 5: 前端 — 配置文件 (vite, main.js, App.vue, router)

**Files:**
- Modify: `code/algae_image_v2/frontend/vite.config.js`
- Modify: `code/algae_image_v2/frontend/src/main.js`
- Modify: `code/algae_image_v2/frontend/src/App.vue`
- Modify: `code/algae_image_v2/frontend/src/router/index.js`

- [ ] **Step 1: vite.config.js — 配置 proxy 到 FastAPI**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 2: main.js — 注册 Element Plus, ECharts, Pinia, Router**

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ECharts from 'vue-echarts'
import 'echarts'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: {} })  // defaults to Chinese in browser
app.component('v-chart', ECharts)

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

- [ ] **Step 3: App.vue — 全局布局壳**

```vue
<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="brand" @click="$router.push('/')">
        <span class="brand-mark">藻</span>
        <div>
          <h1>藻影知微 有害藻华早期预警平台</h1>
          <p class="subtitle">基于偏振成像与深度学习图像识别的智能监测系统</p>
        </div>
      </div>
    </el-header>
    <el-main>
      <el-menu
        :default-active="currentRoute"
        mode="horizontal"
        :ellipsis="false"
        @select="handleSelect"
        class="nav-menu"
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/detect">检测工具</el-menu-item>
        <el-menu-item index="/history">历史记录</el-menu-item>
        <el-menu-item index="/dashboard">数据统计</el-menu-item>
      </el-menu>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.path)

function handleSelect(index) {
  router.push(index)
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #f0f2f5; }
.app-header {
  background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%);
  color: white;
  display: flex;
  align-items: center;
  height: 72px !important;
}
.brand {
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
}
.brand-mark {
  font-size: 32px;
  background: rgba(255,255,255,0.15);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}
.brand h1 { font-size: 20px; font-weight: 600; color: white; }
.subtitle { font-size: 12px; opacity: 0.75; margin-top: 2px; }
.nav-menu {
  margin: -20px -20px 20px -20px;
  padding: 0 20px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}
.app-container { min-height: 100vh; }
</style>
```

- [ ] **Step 4: router/index.js — 4 条路由**

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomePage.vue'),
  },
  {
    path: '/detect',
    name: 'detect',
    component: () => import('@/views/DetectPage.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryPage.vue'),
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 5: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/
git commit -m "feat: scaffold Vue3 + Vite project with Element Plus, ECharts, Router, Pinia"
```

---

### Task 6: 前端 — API 层

**Files:**
- Create: `code/algae_image_v2/frontend/src/api/index.js`

- [ ] **Step 1: 创建 API 封装**

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,  // 2 min — YOLO inference can be slow
})

// ─── Detection ──────────────────────────────────────────────

/** Upload single image with pipeline visualization */
export function detectVisualize(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/detect/visualize', form)
}

/** Upload single image (simple detection, no viz) */
export function detectSingle(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/detect', form)
}

/** Upload multiple images */
export function detectBatch(files) {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  return api.post('/detect/batch', form)
}

// ─── Dashboard ──────────────────────────────────────────────

export function getStats() {
  return api.get('/dashboard/stats')
}

// ─── History ────────────────────────────────────────────────

export function getHistory(page = 1, limit = 20) {
  return api.get('/history', { params: { page, limit } })
}

export function getHistoryDetail(id) {
  return api.get(`/history/${id}`)
}

export function deleteHistory(id) {
  return api.delete(`/history/${id}`)
}

export default api
```

- [ ] **Step 2: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/src/api/
git commit -m "feat: add API layer (axios) for detection, dashboard, history"
```

---

### Task 7: 前端 — Pinia Store

**Files:**
- Create: `code/algae_image_v2/frontend/src/stores/detect.js`

- [ ] **Step 1: 创建检测状态 Store**

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = ref(null)       // VizDetectResponse | null
  const isProcessing = ref(false)
  const error = ref(null)

  function setResult(result) {
    currentResult.value = result
    error.value = null
  }

  function clearResult() {
    currentResult.value = null
    error.value = null
  }

  function setError(msg) {
    error.value = msg
    currentResult.value = null
  }

  return { currentResult, isProcessing, error, setResult, clearResult, setError }
})
```

---

### Task 8: 前端 — 通用组件

**Files:**
- Create: `code/algae_image_v2/frontend/src/components/StepCard.vue`
- Create: `code/algae_image_v2/frontend/src/components/PipelineViz.vue`
- Create: `code/algae_image_v2/frontend/src/components/StatsCards.vue`
- Create: `code/algae_image_v2/frontend/src/components/ResultTable.vue`

- [ ] **Step 1: StepCard.vue — 单步管线卡片**

```vue
<template>
  <el-card shadow="hover" class="step-card">
    <template #header>
      <div class="step-header">
        <el-tag type="primary" size="small">{{ title }}</el-tag>
      </div>
    </template>
    <el-image
      :src="image"
      fit="contain"
      style="width:100%; max-height:240px; background:#000"
    />
    <p class="step-desc">{{ description }}</p>
  </el-card>
</template>

<script setup>
defineProps({
  title: String,
  image: String,
  description: String,
})
</script>

<style scoped>
.step-card { text-align: center; }
.step-header { display: flex; justify-content: center; }
.step-desc { margin-top: 8px; font-size: 12px; color: #666; line-height: 1.5; }
</style>
```

- [ ] **Step 2: PipelineViz.vue — 5 步管线可视化（并排卡片）**

```vue
<template>
  <div class="pipeline-viz">
    <el-row :gutter="16">
      <el-col :span="24">
        <h3 style="margin-bottom:16px; color:#1a3a5c;">
          <el-icon><Cpu /></el-icon> 偏振检测管线 — 中间结果可视化
        </h3>
      </el-col>
    </el-row>
    <el-row :gutter="12">
      <el-col
        v-for="(step, idx) in steps"
        :key="idx"
        :xs="24"
        :sm="12"
        :md="4"
        :lg="4"
        style="margin-bottom:12px"
      >
        <StepCard
          :title="step.title"
          :image="step.image"
          :description="step.description"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import StepCard from './StepCard.vue'

defineProps({
  steps: { type: Array, required: true },
})
</script>
```

- [ ] **Step 3: StatsCards.vue — 统计卡片行**

```vue
<template>
  <el-row :gutter="16">
    <el-col v-for="card in cards" :key="card.label" :xs="12" :sm="8" :md="4">
      <el-card shadow="hover" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong :style="{ color: card.color || '#1a3a5c' }" class="stat-value">
          {{ card.value }}
        </strong>
        <small class="stat-sub">{{ card.sub }}</small>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
defineProps({
  cards: { type: Array, required: true },
  // Each card: { label, value, sub, color? }
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: #999; display: block; }
.stat-value { font-size: 28px; font-weight: 700; display: block; margin: 4px 0; }
.stat-sub { font-size: 11px; color: #bbb; }
</style>
```

- [ ] **Step 4: ResultTable.vue — 检测结果表格**

```vue
<template>
  <el-table :data="detections" stripe border style="width:100%; margin-top:20px" max-height="400">
    <el-table-column prop="class_name_zh" label="藻种" min-width="140" />
    <el-table-column prop="class_name" label="学名" min-width="160" />
    <el-table-column prop="confidence" label="置信度" width="100" sortable>
      <template #default="{ row }">
        <span :style="{ color: row.confidence > 0.7 ? '#16a34a' : row.confidence > 0.4 ? '#f59e0b' : '#dc2626' }">
          {{ (row.confidence * 100).toFixed(1) }}%
        </span>
      </template>
    </el-table-column>
    <el-table-column prop="risk_level" label="风险等级" width="100">
      <template #default="{ row }">
        <el-tag
          :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
          size="small"
        >
          {{ riskLabel(row.risk_level) }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
defineProps({
  detections: { type: Array, required: true },
})

function riskLabel(level) {
  return { high: '高危', medium: '中危', low: '低危' }[level] || level
}
</script>
```

- [ ] **Step 5: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/src/components/ code/algae_image_v2/frontend/src/stores/
git commit -m "feat: add shared components and Pinia store"
```

---

### Task 9: 前端 — 首页 HomePage.vue

**Files:**
- Create: `code/algae_image_v2/frontend/src/views/HomePage.vue`

- [ ] **Step 1: 创建首页**

```vue
<template>
  <div class="home">
    <el-row :gutter="24" style="margin-bottom:24px">
      <el-col :span="24">
        <el-card shadow="never" class="hero-card">
          <h2 style="color:#1a3a5c; font-size:24px; margin-bottom:12px">
            基于偏振成像与深度学习的藻类智能检测系统
          </h2>
          <p style="color:#666; font-size:15px; line-height:1.8; max-width:800px">
            本系统融合 DoFP 偏振相机、HSV 色彩空间偏振模拟、
            I_enh v2 去散射增强算法与 YOLOv8 深度学习模型，
            实现水体藻类的快速、全自动化分类检测与风险预警。
          </p>
        </el-card>
      </el-col>
    </el-row>

    <!-- Pipeline steps -->
    <el-row :gutter="16" style="margin-bottom:24px">
      <el-col :span="24">
        <h3 style="margin-bottom:16px; color:#1a3a5c;">检测管线</h3>
      </el-col>
    </el-row>
    <el-steps :active="5" align-center finish-status="success">
      <el-step title="偏振采集" description="DoFP相机多角度" />
      <el-step title="偏振模拟" description="HSV色彩空间法" />
      <el-step title="图像增强" description="I_enh v2去散射" />
      <el-step title="YOLO识别" description="深度学习分类框选" />
      <el-step title="融合预警" description="风险分级四级预警" />
    </el-steps>

    <!-- Feature cards -->
    <el-row :gutter="20" style="margin-top:36px">
      <el-col :xs="24" :sm="8" v-for="feat in features" :key="feat.title">
        <el-card shadow="hover" class="feature-card">
          <div class="feature-icon">
            <el-icon :size="32"><component :is="feat.icon" /></el-icon>
          </div>
          <h4>{{ feat.title }}</h4>
          <p>{{ feat.desc }}</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- Quick start button -->
    <div style="text-align:center; margin-top:36px">
      <el-button type="primary" size="large" @click="$router.push('/detect')">
        开始检测 <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
const features = [
  {
    icon: 'Camera',
    title: '偏振成像',
    desc: '基于 DoFP 分焦平面偏振相机，单次曝光获取多角度偏振信息，突破传统明场显微限制。',
  },
  {
    icon: 'Cpu',
    title: '智能识别',
    desc: 'YOLOv8 深度学习模型，5 类 FMPD 藻种高精度检测，置信度与风险等级实时输出。',
  },
  {
    icon: 'Warning',
    title: '风险预警',
    desc: '基于藻种产毒特性与密度阈值，四级预警机制，辅助水质安全管理决策。',
  },
]
</script>

<style scoped>
.home { max-width: 1000px; margin: 0 auto; }
.hero-card { border-left: 4px solid #1a3a5c; }
.feature-card { text-align: center; padding: 8px 0; }
.feature-icon { color: #2d6a9f; margin-bottom: 12px; }
.feature-card h4 { font-size: 16px; margin-bottom: 8px; color: #1a3a5c; }
.feature-card p { font-size: 13px; color: #888; line-height: 1.6; }
</style>
```

- [ ] **Step 2: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/src/views/HomePage.vue
git commit -m "feat: add Home page with pipeline steps and feature cards"
```

---

### Task 10: 前端 — 核心页面 DetectPage.vue

**Files:**
- Create: `code/algae_image_v2/frontend/src/views/DetectPage.vue`

- [ ] **Step 1: 创建检测页面（含管线可视化 + 结果 + 图表）**

```vue
<template>
  <div class="detect-page" style="max-width:1200px; margin:0 auto">
    <!-- Upload area -->
    <el-card shadow="never" style="margin-bottom:20px">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        accept="image/*"
        :on-change="handleFileChange"
        :on-remove="handleRemove"
        :file-list="fileList"
      >
        <el-icon :size="48"><UploadFilled /></el-icon>
        <div style="margin-top:12px; font-size:15px">
          拖拽或<em>点击上传</em>藻类显微图像
        </div>
        <template #tip>
          <div style="margin-top:8px; font-size:12px; color:#999">
            支持 PNG / JPG / TIF / BMP 格式
          </div>
        </template>
      </el-upload>

      <div style="text-align:center; margin-top:16px">
        <el-button
          type="primary"
          size="large"
          :loading="isProcessing"
          :disabled="!selectedFile"
          @click="runDetection"
        >
          {{ isProcessing ? '检测中...' : '开始检测' }}
        </el-button>
      </div>
    </el-card>

    <!-- Error -->
    <el-alert v-if="error" :title="error" type="error" show-icon closable
              style="margin-bottom:20px" @close="error = null" />

    <!-- Pipeline visualization -->
    <PipelineViz v-if="result && result.steps" :steps="result.steps" />

    <!-- Stats cards -->
    <StatsCards
      v-if="result"
      :cards="statsCards"
      style="margin-top:20px"
    />

    <!-- Detection table -->
    <ResultTable v-if="result && result.detections.length" :detections="result.detections" />

    <!-- Charts row -->
    <el-row v-if="result && result.detections.length" :gutter="16" style="margin-top:20px">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>风险分布</template>
          <v-chart :option="riskPieOption" style="height:280px" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>置信度分布</template>
          <v-chart :option="confBarOption" style="height:280px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { detectVisualize } from '@/api'
import PipelineViz from '@/components/PipelineViz.vue'
import StatsCards from '@/components/StatsCards.vue'
import ResultTable from '@/components/ResultTable.vue'

const uploadRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const isProcessing = ref(false)
const result = ref(null)
const error = ref(null)

function handleFileChange(file) {
  selectedFile.value = file.raw
}

function handleRemove() {
  selectedFile.value = null
  result.value = null
  error.value = null
}

async function runDetection() {
  if (!selectedFile.value) return
  isProcessing.value = true
  error.value = null
  result.value = null

  try {
    const res = await detectVisualize(selectedFile.value)
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '检测失败, 请重试'
  } finally {
    isProcessing.value = false
  }
}

const statsCards = computed(() => {
  if (!result.value) return []
  const r = result.value
  const highCount = r.detections.filter(d => d.risk_level === 'high').length
  return [
    { label: '检测总数', value: r.detections.length, sub: '检出藻类个体' },
    { label: '高危预警', value: highCount, sub: '需立即关注', color: highCount ? '#dc2626' : '#16a34a' },
    { label: '质量评分', value: r.q_score.toFixed(2), sub: 'Q Score', color: r.q_score > 0.7 ? '#16a34a' : '#f59e0b' },
    { label: '处理耗时', value: (r.processing_time_ms / 1000).toFixed(1) + 's', sub: '端到端时间' },
    { label: '使用模型', value: r.steps ? 'YOLOv8l' : '--', sub: 'FMPD 5类' },
  ]
})

const riskPieOption = computed(() => {
  const dist = { high: 0, medium: 0, low: 0 }
  result.value?.detections.forEach(d => { dist[d.risk_level]++ })
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      label: { show: true, formatter: '{b}: {c}' },
      data: [
        { value: dist.high, name: '高危', itemStyle: { color: '#dc2626' } },
        { value: dist.medium, name: '中危', itemStyle: { color: '#f59e0b' } },
        { value: dist.low, name: '低危', itemStyle: { color: '#16a34a' } },
      ],
    }],
  }
})

const confBarOption = computed(() => {
  const names = result.value?.detections.map(d => d.class_name_zh) || []
  const confs = result.value?.detections.map(d => +(d.confidence * 100).toFixed(1)) || []
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '置信度 (%)', max: 100 },
    series: [{
      type: 'bar',
      data: confs,
      itemStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#2d6a9f' },
            { offset: 1, color: '#1a3a5c' },
          ],
        },
      },
    }],
    grid: { left: 50, right: 20, top: 20, bottom: 60 },
  }
})
</script>
```

- [ ] **Step 2: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/src/views/DetectPage.vue
git commit -m "feat: add Detect page with pipeline viz, result table, and charts"
```

---

### Task 11: 前端 — 历史记录 HistoryPage.vue

**Files:**
- Create: `code/algae_image_v2/frontend/src/views/HistoryPage.vue`

- [ ] **Step 1: 创建历史记录页面**

```vue
<template>
  <div class="history-page" style="max-width:1000px; margin:0 auto">
    <el-card shadow="never">
      <template #header>
        <span style="font-size:16px; font-weight:600">检测历史记录</span>
      </template>

      <el-table :data="items" stripe v-loading="loading" empty-text="暂无检测记录">
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="created_at" label="检测时间" width="180" />
        <el-table-column prop="q_score" label="质量评分" width="100">
          <template #default="{ row }">{{ row.q_score?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
              size="small"
            >
              {{ { high: '高危', medium: '中危', low: '低危' }[row.risk_level] }}
            </el-tag>
            <span v-else style="color:#ccc">--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showDetail(row.id)">详情</el-button>
            <el-button size="small" type="danger" @click="removeItem(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > limit"
        style="margin-top:16px; justify-content:center"
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="limit"
        v-model:current-page="page"
        @current-change="fetchHistory"
      />
    </el-card>

    <!-- Detail dialog -->
    <el-dialog v-model="dialogVisible" title="检测详情" width="700px">
      <div v-if="detail" style="max-height:500px; overflow-y:auto">
        <ResultTable v-if="detail.detections?.length" :detections="detail.detections" />
        <el-empty v-else description="该记录无检测结果" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getHistory, getHistoryDetail, deleteHistory } from '@/api'
import ResultTable from '@/components/ResultTable.vue'

const items = ref([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const dialogVisible = ref(false)
const detail = ref(null)

async function fetchHistory() {
  loading.value = true
  try {
    const res = await getHistory(page.value, limit)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function showDetail(id) {
  try {
    const res = await getHistoryDetail(id)
    detail.value = res.data
    dialogVisible.value = true
  } catch (e) {
    // 404 etc — silently fail in demo
  }
}

async function removeItem(id) {
  try {
    await deleteHistory(id)
    fetchHistory()
  } catch (e) {
    // silently fail
  }
}

onMounted(fetchHistory)
</script>
```

- [ ] **Step 2: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/src/views/HistoryPage.vue
git commit -m "feat: add History page with paginated table and detail dialog"
```

---

### Task 12: 前端 — 数据统计 DashboardPage.vue

**Files:**
- Create: `code/algae_image_v2/frontend/src/views/DashboardPage.vue`

- [ ] **Step 1: 创建数据统计页面**

```vue
<template>
  <div class="dashboard-page" style="max-width:1000px; margin:0 auto">
    <!-- Stats cards -->
    <StatsCards :cards="statsCards" style="margin-bottom:20px" />

    <!-- Charts row -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>藻种分布</template>
          <v-chart :option="classPieOption" style="height:300px" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>风险等级分布</template>
          <v-chart :option="riskBarOption" style="height:300px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent detections -->
    <el-card shadow="never">
      <template #header>最近检测</template>
      <el-table :data="recent" stripe size="small" empty-text="暂无数据">
        <el-table-column prop="filename" label="文件名" min-width="160" />
        <el-table-column prop="risk_level" label="风险" width="80">
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
              size="small"
            >
              {{ { high: '高', medium: '中', low: '低' }[row.risk_level] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="q_score" label="质量分" width="80">
          <template #default="{ row }">{{ row.q_score?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStats } from '@/api'
import StatsCards from '@/components/StatsCards.vue'

const stats = ref(null)
const recent = ref([])

async function fetchStats() {
  try {
    const res = await getStats()
    stats.value = res.data
    recent.value = res.data.recent_detections || []
  } catch (e) {
    // silently fail
  }
}

const statsCards = computed(() => {
  if (!stats.value) return []
  const s = stats.value
  const highCount = s.risk_distribution?.high || 0
  return [
    { label: '总检测次数', value: s.total_detections, sub: '累计检测样本' },
    { label: '今日检测', value: s.today_count, sub: '当日处理量' },
    { label: '高危预警', value: highCount, sub: '需立即关注', color: highCount ? '#dc2626' : '#16a34a' },
    { label: '活跃藻种', value: Object.keys(s.class_distribution || {}).length, sub: '检出类别数' },
  ]
})

const classPieOption = computed(() => {
  const dist = stats.value?.class_distribution || {}
  const data = Object.entries(dist).map(([name, value]) => ({ name, value }))
  return {
    tooltip: { trigger: 'item' },
    legend: { type: 'scroll', bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      data,
      label: { formatter: '{b}: {c}' },
    }],
  }
})

const riskBarOption = computed(() => {
  const dist = stats.value?.risk_distribution || {}
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['高危', '中危', '低危'] },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: [
        { value: dist.high || 0, itemStyle: { color: '#dc2626' } },
        { value: dist.medium || 0, itemStyle: { color: '#f59e0b' } },
        { value: dist.low || 0, itemStyle: { color: '#16a34a' } },
      ],
    }],
    grid: { left: 50, right: 20, top: 10, bottom: 30 },
  }
})

onMounted(fetchStats)
</script>
```

- [ ] **Step 2: 提交**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/frontend/src/views/DashboardPage.vue
git commit -m "feat: add Dashboard page with stats cards and echarts"
```

---

### Task 13: 端到端验证

- [ ] **Step 1: 启动 FastAPI 后端**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2
conda activate ican
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Expected: `[Startup] Pipeline ready — Algae Image V2 (HSV, FMPD 5-class)`

- [ ] **Step 2: 测试 /detect/visualize 接口**

```bash
# 在另一个终端，用 curl 测试（需要一张测试图片）
curl -X POST http://localhost:8000/api/v1/detect/visualize \
  -F "file=@/path/to/any/test/image.png"
```

Expected: JSON 响应中包含 `steps` 数组（5 个元素，每个有 title/image/description），`detections` 数组，`q_score` 等。

- [ ] **Step 3: 启动 Vite 前端**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage/code/algae_image_v2/frontend
npm run dev
```

访问 `http://localhost:5173`，验证：
- 首页：管线步骤 + 功能卡片
- 检测工具：上传图片 → 看到 5 步管线可视化 + 结果表格 + 图表
- 历史记录：表格 + 分页
- 数据统计：卡片 + ECharts 图表

- [ ] **Step 4: 提交全部剩余变更**

```bash
cd /Users/lanyuanzhe/Documents/GitHub/algaeimage
git add code/algae_image_v2/backend/ code/algae_image_v2/frontend/
git commit -m "feat: complete Vue3 + FastAPI competition platform"
```

---

## 自审清单

1. **Spec 覆盖**:
   - ✓ 4 页（首页/检测/历史/统计）→ Tasks 9-12
   - ✓ 5 步管线可视化 → Task 8 (PipelineViz) + Task 1 (后端)
   - ✓ 后端 pipeline.py 新增方法 → Task 1
   - ✓ 后端新路由 → Task 3
   - ✓ 后端 schemas → Task 2
   - ✓ Vue3 脚手架 → Task 4
   - ✓ API 层 → Task 6
   - ✓ Pinia store → Task 7
   - ✓ 组件库 → Task 8

2. **无占位符**: 所有代码完整，无 TBD/TODO/占位描述。

3. **类型一致性**: `VizStep.title/image/description` 在 schema、pipeline、StepCard props 中一致；`DetectionItem` 与 ResultTable 列对应一致。
