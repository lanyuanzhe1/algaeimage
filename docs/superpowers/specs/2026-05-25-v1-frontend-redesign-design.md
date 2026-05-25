# V1.0 Frontend Redesign — Design Spec

**Date**: 2026-05-25
**Status**: Approved
**Context**: Redesign `code/algae_image_v1/frontend/index.html` from simple tab-based tool page to a polished monitoring dashboard, using `algae_guardian_platform.html` as the visual template.

---

## 1. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Overall approach | Hybrid — Dashboard homepage + nav-switchable tool pages | Combines monitoring overview with operational depth |
| Visual template | `algae_guardian_platform.html` | Proven polished design; users already familiar with it |
| Color scheme | Blue-cyan primary + 4-level risk (red/orange/yellow/green) | Tech/optical/monitoring feel; polarimetric detection identity |
| Unfinished features | Static placeholder panels (not hidden) | Shows product roadmap; avoids looking incomplete |
| CSS architecture | Single `style.css` with CSS variables | Matches current architecture; no build tools needed |
| JS architecture | Keep `app.js` + `detection.js` + `dashboard.js` separation, add new modules | Preserve existing logic; add dashboard module |
| Chart library | Keep Chart.js 4.4.0 CDN | Already integrated; sufficient for dashboard needs |

## 2. Design Tokens (CSS Variables)

```css
:root {
  /* Primary — blue-cyan */
  --primary: #1976d2;
  --primary-dark: #1565c0;
  --primary-light: #43b7ff;
  --cyan: #0891b2;
  --cyan-light: #39d7c8;

  /* Risk — 4-level */
  --risk-red: #dc2626;
  --risk-red-bg: rgba(251, 78, 93, .12);
  --risk-orange: #ea580c;
  --risk-orange-bg: rgba(251, 146, 60, .1);
  --risk-yellow: #ca8a04;
  --risk-yellow-bg: rgba(250, 204, 21, .1);
  --risk-green: #16a34a;
  --risk-green-bg: rgba(74, 222, 128, .1);

  /* Neutrals */
  --bg: #f4f8fc;
  --panel: #ffffff;
  --panel-2: #f7fbff;
  --line: #d8e5f2;
  --line-soft: rgba(15, 40, 70, .08);
  --text: #162235;
  --muted: #65778b;

  /* Shadows */
  --shadow: 0 18px 46px rgba(28, 74, 121, .12);
  --shadow-sm: 0 1px 3px rgba(28, 74, 121, .06);

  /* Spacing & radius */
  --radius: 8px;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;

  /* Typography */
  --font-mono: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}
```

## 3. Page Structure

### 3.1 Dashboard Homepage (default view)

3-column layout inspired by the template:

```
┌─────────────────────────────────────────────────────┐
│ Top Bar: Brand | System Status | Refresh | Export    │
├─────────────────────────────────────────────────────┤
│ Pipeline Bar: ①采集 → ②重建 → ③增强 → ④YOLO → ⑤预警  │
├──────────┬──────────────────────────┬───────────────┤
│ Left     │ Center                   │ Right         │
│ 280px    │ fluid                    │ 300px         │
│          │                          │               │
│ Stats    │ Detection Upload Zone    │ Recent        │
│ Cards    │ (drag-drop / click)      │ Detections    │
│          │                          │               │
│ Pipeline │ Result Display           │ Risk Summary  │
│ Status   │ (image + detections)     │ (placeholder) │
│          │                          │               │
│ Quick    │ Charts: Class Dist       │ Data Loop     │
│ Actions  │ + Risk Distribution      │ (placeholder) │
└──────────┴──────────────────────────┴───────────────┘
```

### 3.2 Navigation

Top bar contains 6 navigation items:

| Nav Item | Status | Description |
|----------|--------|-------------|
| 首页 Dashboard | Active | Default landing page |
| 检测工具 Detect | Active | Full detection workflow (upload → result) |
| 历史记录 History | Active | Searchable paginated detection history |
| 数据统计 Stats | Active | Charts, trends, aggregated statistics |
| 设备管理 Devices | Placeholder | Static "coming soon" panel |
| 人工复核 Review | Placeholder | Static "coming soon" panel |

### 3.3 Responsive Breakpoints

- `> 1200px`: Full 3-column layout
- `900px–1200px`: 2-column (left + center, right stacks below)
- `< 900px`: Single column, all panels stack vertically

## 4. Component Inventory

### 4.1 Reused from Current V1 (functional, restyle only)

- **Upload Zone** — drag-drop + file picker + folder selection. Core logic in `detection.js` unchanged.
- **Result Panel** — detection image + species list + risk badges + Q score. Restyle to match template cards.
- **History Table** — paginated table with risk badges. Restyle to match template table style.
- **Dashboard Charts** — Chart.js class distribution + risk distribution. Keep chart logic, restyle container.

### 4.2 New from Template (adapt to real data)

- **Top Bar** — Brand + system status indicator + action buttons (refresh, export report). Export button triggers report modal.
- **Pipeline Bar** — 5-step visualization showing processing stages. Steps highlight based on current context (detection page highlights ①–⑤ sequentially during processing).
- **Metrics Cards** — 5 cards across top: 总检测, 今日检测, 高危预警, 模型版本, 数据闭环样本数. Populated from backend `/api/v1/dashboard/stats`.
- **Left Panel** — Stats + pipeline status + quick-action buttons. Replaces template's site list (V1 is single-machine, no multi-site).
- **Right Panel** — Recent detections list + risk summary placeholder + data loop placeholder.

### 4.3 Placeholder Panels (static, no backend)

- **Devices Page** — "设备管理模块将在后续版本开放" with template-style card layout and a mock device card showing camera/light/network status bars at 100%.
- **Review Page** — "人工复核模块将在后续版本开放" with mock review workflow visualization (collect → identify → review → retrain loop diagram).
- **Right Panel Risk Summary** — Static risk level legend + description text.
- **Right Panel Data Loop** — 4-step circular diagram (采集→识别→复核→再训练) with first 2 steps marked done.

## 5. Data Flow

```
Backend APIs (existing, unchanged)
    │
    ├── GET /api/v1/dashboard/stats ──→ Metrics cards + charts
    ├── POST /api/v1/detect ──→ Detection result panel
    ├── POST /api/v1/detect/batch ──→ Batch progress + results
    └── GET /api/v1/history ──→ History table
```

No backend changes required. All existing API contracts preserved. Frontend-only change.

## 6. File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/index.html` | **Rewrite** | New HTML structure with all panels |
| `frontend/css/style.css` | **Rewrite** | New design tokens + all component styles |
| `frontend/js/app.js` | **Modify** | Add navigation + dashboard rendering |
| `frontend/js/detection.js` | **Minor edit** | Adjust DOM selectors if element IDs change |
| `frontend/js/dashboard.js` | **Modify** | Adapt chart containers to new layout |
| `frontend/js/dashboard-home.js` | **New** | Dashboard homepage rendering (metrics, recent, pipeline) |

## 7. Implementation Constraints

- **No build tools** — must remain plain HTML/CSS/JS
- **No new dependencies** — Chart.js 4.4.0 CDN only
- **Existing JS logic preserved** — detection, history, dashboard API calls should work with minimal changes
- **Backend unchanged** — all existing API routes must work as-is
- **Single `index.html`** — SPA structure, no multi-page navigation
- **`run.bat` still works** — no new startup requirements

## 8. Out of Scope

- Device management actual functionality
- Manual review actual functionality
- Real-time WebSocket data streaming
- Multi-site/multi-device support (V1 is single-machine)
- Dark mode
- i18n / multi-language
