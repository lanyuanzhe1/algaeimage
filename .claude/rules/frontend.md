---
paths: code/algae_image_v1/frontend/**
---

# V1 Frontend Rules (Legacy — vanilla HTML/CSS/JS)

## Stack constraints

- **No framework, no build tools.** Pure HTML/CSS/JS. No React, Vue, npm, webpack, TypeScript.
- **Chart.js 4.4.0 via CDN** — the only external dependency.
- **SPA pattern** — single `index.html`, all routing via JS tab switching, no page reloads.
- **Static files served by FastAPI** — mounted at `/app/` via `StaticFiles`.

## Component structure

```
frontend/
  index.html          ← Single entry point. 6-page SPA.
  css/style.css       ← All styles here. No inline styles in HTML.
  js/
    app.js            ← Tab switching, API calls, global state
    detection.js      ← Upload, preview, result rendering
    dashboard.js      ← Chart.js stats rendering
```

## Key patterns

- Folder selection uses `webkitdirectory` attribute on `<input type="file">` plus drag-drop recursive traversal.
- API base URL: `/api/v1/`. All calls go through `fetch()` in `app.js`.
- No CORS concerns — same origin as backend.

## NEVER

- Add npm/node_modules/package.json to frontend/
- Use React, Vue, Angular, or any SPA framework
- Add a CSS framework (no Tailwind, Bootstrap) — custom CSS only
- Use inline styles or `<style>` blocks in HTML — all CSS in `style.css`


---
paths: code/algae_image_v2/frontend/**
---

# V2 Frontend Rules (Current — Vue3 + Vite + Element Plus)

## Stack (2026-06-08 migration)

- **Vue3** (Composition API, `<script setup>`) + **Vite 6** + **Element Plus 2.9** + **ECharts 5.6** + **Pinia** + **Vue Router 4** + **Axios**.
- **npm** managed (`package.json`). `npm install` before first use.
- `npm run dev` → Vite dev server port 5173, hot reload, proxies `/api` + `/static` to `http://127.0.0.1:8000`.
- `npm run build` → production output to `dist/` (committed to git for offline exe packaging).

## ECharts: MUST register renderer

ECharts 5.x is tree-shakable by default. Importing `vue-echarts` without registering CanvasRenderer causes `Renderer 'undefined' is not imported` at runtime. In `src/main.js`, always keep:

```js
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
use([CanvasRenderer, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])
```

When adding new chart types, add them to the `use()` call.

## Component structure

```
frontend/src/
  main.js              ← Entry: Vue app, Pinia, Router, Element Plus, ECharts registration
  App.vue              ← Shell: header brand + nav menu + <router-view>
  api/index.js         ← Axios instance (baseURL=/api/v1) + endpoint functions
  router/index.js      ← 4 routes: /, /detect, /history, /dashboard
  stores/detect.js     ← Pinia store for detection state
  views/
    HomePage.vue       ← Pipeline overview + feature cards
    DetectPage.vue     ← File upload + pipeline viz + result table + charts
    HistoryPage.vue    ← Detection history table
    DashboardPage.vue  ← Stats cards + pie/bar charts
  components/
    PipelineViz.vue    ← Renders 5 VizStep cards with base64 images
    ResultTable.vue    ← Detection results table (Element Plus el-table)
    StatsCards.vue     ← Summary stat cards
    StepCard.vue       ← Single pipeline step card
```

## Key patterns

- All API calls go through `api/index.js` functions (e.g., `detectVisualize(file)`, `getStats()`).
- Vite proxy handles `/api` → backend during dev. In production, FastAPI serves `dist/` as static files.
- File upload: `el-upload` with `auto-upload=false`, file set via `on-change` → `file.raw`.
- Pipeline visualization: the 5 `VizStep` images are base64 data URIs embedded in JSON.
- Error display: `el-alert` banner, not `alert()`. Errors from `e.response?.data?.detail`.

## NEVER

- Remove the ECharts `use()` registration from main.js (will break all charts)
- Use Options API — all components use `<script setup>` Composition API
- Add CSS frameworks beyond Element Plus (no Tailwind, Bootstrap)
- Import from `echarts` without also registering renderer/charts/components
