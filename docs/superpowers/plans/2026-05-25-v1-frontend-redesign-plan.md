# V1 Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `index.html` from simple tab-based tool page to polished blue-cyan monitoring dashboard, using `algae_guardian_platform.html` visual style, while preserving all existing JS detection/dashboard logic.

**Architecture:** Single SPA with dashboard homepage as default view. 6 nav items switch content panels via CSS display toggling. All existing DOM element IDs preserved so `detection.js` and `dashboard.js` need zero or minimal changes. New `dashboard-home.js` handles homepage metrics, pipeline status, and recent detections rendering.

**Tech Stack:** Plain HTML/CSS/JS, Chart.js 4.4.0 CDN, no build tools, no new dependencies.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/index.html` | Rewrite | All HTML structure: topbar, nav, pipeline bar, dashboard homepage (3-column), detect/history/stats/devices/review panels |
| `frontend/css/style.css` | Rewrite | Blue-cyan design tokens, all component styles, responsive breakpoints |
| `frontend/js/app.js` | Modify | Add `updatePipeline`/`completePipeline`/`resetPipeline`, nav switching, dashboard homepage init, report modal |
| `frontend/js/detection.js` | No changes | Already references correct element IDs and pipeline functions |
| `frontend/js/dashboard.js` | Minor edit | Update `statAvgQ`/`statClassCount` references (new IDs in HTML) |
| `frontend/js/dashboard-home.js` | Create | Homepage metrics cards rendering, recent detections list, pipeline status, risk summary placeholder |

---

### Task 1: Rewrite CSS with Blue-Cyan Design System

**Files:**
- Rewrite: `code/algae_image_v1/frontend/css/style.css`

- [ ] **Step 1: Write the new CSS file**

Write `code/algae_image_v1/frontend/css/style.css`:

```css
/* ═══════════════════════════════════════════════════════════════════════════
   Algae Guardian V1.0 — Blue-Cyan Design System
   ═══════════════════════════════════════════════════════════════════════════ */

:root {
  /* Primary — blue-cyan */
  --primary: #1976d2;
  --primary-dark: #1565c0;
  --primary-light: #43b7ff;
  --cyan: #0891b2;
  --cyan-light: #39d7c8;

  /* Risk — 4-level */
  --risk-red: #dc2626;
  --risk-red-bg: rgba(251,78,93,.12);
  --risk-orange: #ea580c;
  --risk-orange-bg: rgba(251,146,60,.1);
  --risk-yellow: #ca8a04;
  --risk-yellow-bg: rgba(250,204,21,.1);
  --risk-green: #16a34a;
  --risk-green-bg: rgba(74,222,128,.1);

  /* Neutrals */
  --bg: #f4f8fc;
  --panel: #ffffff;
  --panel-2: #f7fbff;
  --line: #d8e5f2;
  --line-soft: rgba(15,40,70,.08);
  --text: #162235;
  --muted: #65778b;

  /* Shadows */
  --shadow: 0 18px 46px rgba(28,74,121,.12);
  --shadow-sm: 0 1px 3px rgba(28,74,121,.06);

  /* Spacing & radius */
  --radius: 8px;
  --radius-sm: 4px;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* Typography */
  --font-mono: 'SF Mono','Cascadia Code','Consolas',monospace;
}

/* ── Reset & Base ── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:15px}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
  color:var(--text);line-height:1.6;min-height:100vh;
  background:linear-gradient(135deg,rgba(25,118,210,.08),transparent 34rem),
             linear-gradient(180deg,#ffffff 0%,var(--bg) 44%,#edf5fb 100%);
}
a{color:var(--primary-light);text-decoration:none}
a:hover{text-decoration:underline}

/* ── App Container ── */
.app{width:min(1440px,calc(100vw - 32px));margin:0 auto;padding:18px 0 28px}

/* ── Top Bar ── */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  min-height:60px;padding:0 6px;gap:18px;
}
.brand{display:flex;align-items:center;gap:14px;min-width:0}
.brand-mark{
  width:42px;height:42px;display:grid;place-items:center;
  border:1px solid rgba(67,183,255,.6);
  background:linear-gradient(145deg,rgba(67,183,255,.2),rgba(57,215,200,.12));
  border-radius:8px;box-shadow:inset 0 0 18px rgba(25,118,210,.16);
  color:var(--primary);font-weight:800;font-size:20px;flex-shrink:0;
}
.brand h1{margin:0;font-size:clamp(22px,2vw,28px);letter-spacing:0;line-height:1.1}
.brand .subtitle{margin:5px 0 0;color:var(--muted);font-size:13px}
.brand .subtitle strong{color:var(--primary);font-weight:600}
.top-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}

.btn,.status-pill{
  height:36px;border-radius:8px;border:1px solid var(--line);color:var(--text);
  background:rgba(255,255,255,.86);display:inline-flex;align-items:center;
  gap:8px;padding:0 12px;white-space:nowrap;font:inherit;cursor:pointer;
  transition:all .15s;
}
.btn:hover{border-color:rgba(25,118,210,.4);transform:translateY(-1px)}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none}

.btn-primary{
  background:linear-gradient(180deg,rgba(25,118,210,.12),rgba(25,118,210,.06));
  border-color:rgba(25,118,210,.34);font-weight:600;
}
.btn-primary:hover{background:linear-gradient(180deg,rgba(25,118,210,.18),rgba(25,118,210,.1))}
.btn-danger{background:var(--risk-red);color:#fff;border-color:var(--risk-red)}
.btn-danger:hover{background:#b91c1c}
.btn-outline{background:transparent;color:var(--primary);border-color:var(--primary)}
.btn-outline:hover{background:rgba(25,118,210,.06)}
.btn-sm{padding:5px 12px;font-size:.8rem;height:auto}
.btn-group{display:flex;gap:var(--spacing-sm)}

.status-dot{
  width:8px;height:8px;border-radius:99px;background:var(--risk-green);
  box-shadow:0 0 12px rgba(22,163,74,.35);
}

/* ── Navigation Bar ── */
.navbar{
  display:flex;background:var(--panel);border:1px solid var(--line);
  border-radius:var(--radius);margin-top:14px;padding:0 4px;
  box-shadow:var(--shadow);gap:2px;
}
.nav-btn{
  padding:10px 18px;border:none;background:none;color:var(--muted);
  font-size:.88rem;font-weight:500;cursor:pointer;border-radius:6px;
  transition:all .18s;white-space:nowrap;
}
.nav-btn:hover{color:var(--primary);background:rgba(25,118,210,.05)}
.nav-btn.active{
  color:var(--text);background:rgba(25,118,210,.1);
  border-color:rgba(25,118,210,.3);font-weight:600;
}
.nav-btn:disabled{color:var(--muted);opacity:.5;cursor:not-allowed}
.nav-btn:disabled:hover{background:none;color:var(--muted)}

/* ── Pipeline Bar ── */
.pipeline-bar{
  display:flex;align-items:center;justify-content:space-between;gap:4px;
  margin-top:14px;padding:10px 16px;
  background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(247,251,255,.96));
  border:1px solid var(--line);border-radius:var(--radius);
  box-shadow:var(--shadow);
}
.pipe-step{display:flex;align-items:center;gap:8px;flex:1;min-width:0}
.pipe-step .num{
  width:26px;height:26px;border-radius:99px;display:grid;place-items:center;
  font-size:12px;font-weight:800;background:var(--line-soft);color:var(--muted);
  flex-shrink:0;transition:.2s;
}
.pipe-step.active .num{
  background:linear-gradient(135deg,var(--primary),var(--cyan));
  color:#fff;box-shadow:0 0 16px rgba(25,118,210,.35);
}
.pipe-step.done .num{background:var(--risk-green);color:#fff}
.pipe-step .info{min-width:0}
.pipe-step .info strong{display:block;font-size:13px;line-height:1.2}
.pipe-step .info small{color:var(--muted);font-size:11px}
.pipe-arrow{color:var(--line);font-size:18px;flex-shrink:0;margin:0 2px}

/* ── Metrics Cards Row ── */
.metrics-row{
  display:grid;grid-template-columns:repeat(5,minmax(0,1fr));
  gap:12px;margin-top:12px;
}
.metric-card{
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:15px 16px;box-shadow:var(--shadow-sm);position:relative;overflow:hidden;
}
.metric-card::after{
  content:"";position:absolute;inset:auto 14px 0 14px;height:2px;
  background:linear-gradient(90deg,transparent,rgba(25,118,210,.42),transparent);
  opacity:.5;
}
.metric-card .metric-label{display:block;color:var(--muted);font-size:13px}
.metric-card .metric-value{display:block;margin-top:8px;font-size:28px;font-weight:700;letter-spacing:0}
.metric-card .metric-sub{color:var(--muted);font-size:12px}
.metric-card .metric-value.danger{color:var(--risk-red)}

/* ── Main 3-Column Layout ── */
.main-layout{
  display:grid;grid-template-columns:280px minmax(0,1fr) 300px;
  gap:14px;margin-top:14px;
}
.panel{
  background:linear-gradient(180deg,rgba(255,255,255,.98),rgba(247,251,255,.98));
  border:1px solid var(--line);border-radius:var(--radius);
  box-shadow:var(--shadow);min-width:0;
}
.panel-head{
  min-height:54px;padding:14px 16px 0;
  display:flex;align-items:flex-start;justify-content:space-between;gap:12px;
}
.panel-title{margin:0;font-size:16px;font-weight:700}
.panel-subtitle{margin:5px 0 0;color:var(--muted);font-size:12px}
.panel-body{padding:14px 16px 16px}

/* ── Left Panel: Stats + Actions ── */
.stat-list{padding:10px;display:grid;gap:8px}
.stat-item{
  border:1px solid var(--line-soft);border-radius:var(--radius);
  padding:12px;background:rgba(247,251,255,.72);text-align:center;
}
.stat-item .stat-num{font-size:24px;font-weight:700;color:var(--primary)}
.stat-item .stat-text{font-size:12px;color:var(--muted)}
.quick-actions{padding:10px;display:grid;gap:6px}

/* ── Center Panel: Detection ── */
.upload-zone{
  border:2px dashed var(--line);border-radius:var(--radius);
  padding:var(--spacing-xl);text-align:center;cursor:pointer;
  transition:border-color .2s,background .2s;background:var(--panel);position:relative;
}
.upload-zone:hover,.upload-zone.drag-over{border-color:var(--primary-light);background:rgba(25,118,210,.04)}
.upload-zone .upload-icon{font-size:2.4rem;color:var(--muted);margin-bottom:var(--spacing-sm);display:block}
.upload-zone .upload-text{color:var(--muted);font-size:.9rem;margin-bottom:var(--spacing-xs)}
.upload-zone .upload-hint{color:var(--muted);font-size:.78rem;opacity:.7}
.upload-zone input[type="file"]{display:none}
.preview-thumb{
  max-width:100%;max-height:200px;border-radius:var(--radius-sm);
  margin-top:var(--spacing-sm);border:1px solid var(--line);object-fit:contain;
}

/* ── Result Panel ── */
.result-panel{
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;min-height:300px;
}
.result-panel .panel-header{
  padding:var(--spacing-sm) var(--spacing-md);background:var(--panel-2);
  border-bottom:1px solid var(--line);font-weight:600;font-size:.9rem;
  display:flex;align-items:center;justify-content:space-between;
}
.result-panel .panel-body{padding:var(--spacing-md);overflow-y:auto;max-height:70vh}
.result-image{width:100%;border-radius:var(--radius-sm);border:1px solid var(--line);margin-bottom:var(--spacing-md)}
.result-meta{display:flex;gap:var(--spacing-md);flex-wrap:wrap;margin-bottom:var(--spacing-md)}
.result-meta .meta-item{font-size:.82rem;color:var(--muted)}
.result-meta .meta-item strong{color:var(--text);font-weight:600}

/* ── Detection List ── */
.detect-list{list-style:none;display:flex;flex-direction:column;gap:var(--spacing-sm)}
.detect-item{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px;background:var(--panel-2);border-radius:var(--radius-sm);
  border-left:3px solid transparent;gap:var(--spacing-sm);
}
.detect-item.risk-high{border-left-color:var(--risk-red);background:var(--risk-red-bg)}
.detect-item.risk-medium{border-left-color:var(--risk-yellow);background:var(--risk-yellow-bg)}
.detect-item.risk-low{border-left-color:var(--risk-green);background:var(--risk-green-bg)}
.detect-item .detect-name{font-weight:500;font-size:.88rem;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.detect-item .detect-conf{font-size:.78rem;color:var(--muted);white-space:nowrap}

/* ── Risk Badge ── */
.risk-badge{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:56px;height:24px;padding:0 9px;border-radius:7px;
  border:1px solid currentColor;font-size:12px;font-weight:700;white-space:nowrap;
}
.risk-badge.risk-high{color:var(--risk-red);background:var(--risk-red-bg)}
.risk-badge.risk-medium{color:var(--risk-yellow);background:var(--risk-yellow-bg)}
.risk-badge.risk-low{color:var(--risk-green);background:var(--risk-green-bg)}

/* ── Q Score ── */
.q-score{display:inline-flex;align-items:center;gap:4px;font-family:var(--font-mono);font-size:.85rem;font-weight:600;color:var(--primary)}
.q-score .q-label{font-family:inherit;font-weight:400;color:var(--muted);font-size:.75rem}

/* ── Right Panel: Recent + Placeholders ── */
.recent-list{padding:10px 16px 16px;display:grid;gap:10px}
.recent-item{
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  border:1px solid var(--line-soft);border-radius:var(--radius);
  padding:10px;background:rgba(247,251,255,.72);font-size:13px;
}
.recent-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}

/* ── Placeholder Sections ── */
.placeholder-section{
  padding:14px 16px 16px;text-align:center;
}
.placeholder-section .ph-icon{font-size:2.5rem;display:block;margin-bottom:var(--spacing-sm);color:var(--muted);opacity:.5}
.placeholder-section .ph-title{font-weight:600;color:var(--muted);margin-bottom:4px}
.placeholder-section .ph-desc{font-size:12px;color:var(--muted);opacity:.7;line-height:1.6}

/* ── Loop Diagram (placeholder) ── */
.loop-flow{
  padding:10px 16px 4px;display:grid;grid-template-columns:1fr 1fr;gap:8px;
}
.loop-node{
  display:flex;flex-direction:column;align-items:center;gap:4px;
  padding:10px 6px;border:1px solid var(--line-soft);border-radius:var(--radius);
  background:rgba(247,251,255,.72);text-align:center;font-size:12px;
}
.loop-node .dot{
  width:28px;height:28px;border-radius:99px;display:grid;place-items:center;
  font-size:14px;font-weight:800;background:var(--line-soft);color:var(--muted);
}
.loop-node.done .dot{background:var(--risk-green);color:#fff}
.loop-node label{font-weight:600;font-size:13px}

/* ── Progress Bar ── */
.progress-bar-wrap{display:none;margin-top:var(--spacing-md)}
.progress-bar-wrap.visible{display:block}
.progress-bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden}
.progress-bar .progress-fill{
  height:100%;background:linear-gradient(90deg,var(--primary),var(--cyan-light));
  border-radius:4px;width:0%;transition:width .3s ease;
}
.progress-text{font-size:.8rem;color:var(--muted);margin-top:var(--spacing-xs);text-align:center}

/* ── Charts Area (Dashboard/Stats page) ── */
.charts-grid{
  display:grid;grid-template-columns:repeat(2,1fr);gap:var(--spacing-md);
}
.chart-card{
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:var(--spacing-md);box-shadow:var(--shadow);
}
.chart-card .chart-title{font-weight:600;font-size:.92rem;margin-bottom:var(--spacing-md)}
.chart-card canvas{width:100%!important;max-height:340px}

/* ── Table ── */
.table-wrap{overflow-x:auto}
table{
  width:100%;border-collapse:collapse;font-size:13px;
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
}
table thead{background:var(--panel-2)}
table th{
  text-align:left;padding:11px 14px;font-size:.8rem;font-weight:600;
  color:var(--muted);text-transform:uppercase;letter-spacing:.3px;
  border-bottom:1px solid var(--line);white-space:nowrap;
}
table td{padding:10px 14px;font-size:.88rem;border-bottom:1px solid var(--line-soft);vertical-align:middle}
table tbody tr:hover{background:rgba(25,118,210,.04)}
table tbody tr:last-child td{border-bottom:none}

/* ── Pagination ── */
.pagination{display:flex;justify-content:center;align-items:center;gap:var(--spacing-xs);margin-top:var(--spacing-lg)}
.pagination .page-btn{
  padding:6px 12px;border:1px solid var(--line);border-radius:var(--radius-sm);
  background:var(--panel);cursor:pointer;font-size:.85rem;color:var(--text);transition:all .15s;
}
.pagination .page-btn:hover:not(:disabled){background:rgba(25,118,210,.06);border-color:var(--primary);color:var(--primary)}
.pagination .page-btn.active{background:var(--primary);color:#fff;border-color:var(--primary)}
.pagination .page-btn:disabled{opacity:.4;cursor:not-allowed}
.pagination .page-info{font-size:.82rem;color:var(--muted);padding:0 var(--spacing-sm)}

/* ── Empty State ── */
.empty-state{text-align:center;padding:var(--spacing-xl);color:var(--muted)}
.empty-state .empty-icon{font-size:3rem;display:block;margin-bottom:var(--spacing-md)}
.empty-state .empty-text{font-size:.95rem;margin-bottom:var(--spacing-xs)}
.empty-state .empty-hint{font-size:.8rem}

/* ── Page Panel (for dedicated pages: detect/history/stats/devices/review) ── */
.page-panel{display:none}
.page-panel.active{display:block}
.page-panel .page-inner{max-width:1200px;margin:0 auto;padding:var(--spacing-lg) 0}

/* ── Stats Grid (dashboard sub-page) ── */
.stats-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:var(--spacing-md);
  margin-bottom:var(--spacing-lg);
}
.stat-card{
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:var(--spacing-lg);text-align:center;box-shadow:var(--shadow-sm);
}
.stat-card .stat-value{font-size:2rem;font-weight:700;color:var(--primary);line-height:1.2}
.stat-card .stat-value.high-risk{color:var(--risk-red)}
.stat-card .stat-label{font-size:.82rem;color:var(--muted);margin-top:var(--spacing-xs)}

/* ── Toast ── */
.toast{
  position:fixed;bottom:var(--spacing-lg);right:var(--spacing-lg);z-index:9999;
  padding:12px 20px;border-radius:var(--radius);color:#fff;font-size:.88rem;
  font-weight:500;box-shadow:var(--shadow);animation:toast-in .3s ease;max-width:400px;
}
.toast.success{background:var(--risk-green)}
.toast.error{background:var(--risk-red)}
.toast.warning{background:var(--risk-yellow)}
.toast.info{background:var(--primary)}
@keyframes toast-in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}

/* ── Spinner ── */
.spinner{
  display:inline-block;width:18px;height:18px;border:2px solid var(--line);
  border-top-color:var(--primary);border-radius:50%;animation:spin .6s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Modal ── */
.modal{
  position:fixed;inset:0;display:none;align-items:center;justify-content:center;
  padding:20px;background:rgba(0,0,0,.58);z-index:1000;
}
.modal.show{display:flex}
.modal-card{
  width:min(560px,100%);border:1px solid rgba(25,118,210,.28);
  border-radius:var(--radius);background:#ffffff;
  box-shadow:0 30px 90px rgba(28,74,121,.22);padding:22px;
}
.modal-card h2{margin:0 0 12px;font-size:20px}
.modal-card p{margin:8px 0;color:var(--muted);line-height:1.7}
.modal-card .btn{margin-top:16px}

/* ── Utility ── */
.hidden{display:none!important}
.text-center{text-align:center}
.text-muted{color:var(--muted)}
.text-sm{font-size:.82rem}
.mt-md{margin-top:var(--spacing-md)}
.mb-md{margin-bottom:var(--spacing-md)}

/* ── Responsive ── */
@media (max-width:1200px){
  .metrics-row{grid-template-columns:repeat(3,minmax(0,1fr))}
  .main-layout{grid-template-columns:260px minmax(0,1fr)}
  .right-panel{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
  .pipeline-bar{flex-wrap:wrap;gap:6px}
  .pipe-step{flex:0 0 auto}
}
@media (max-width:900px){
  .app{width:min(100% - 20px,720px)}
  .topbar{flex-direction:column;align-items:flex-start}
  .metrics-row{grid-template-columns:1fr 1fr}
  .main-layout,.charts-grid{grid-template-columns:1fr}
  .right-panel{grid-column:auto;display:block}
  .stats-grid{grid-template-columns:1fr}
  .navbar{overflow-x:auto}
  th,td{white-space:normal}
}
@media (max-width:640px){
  .metrics-row{grid-template-columns:1fr}
  .nav-btn{padding:8px 10px;font-size:.78rem}
  .result-meta{flex-direction:column;gap:var(--spacing-xs)}
}
```

- [ ] **Step 2: Verify CSS file was written**

Run: `wc -l e:/code/codex/code/algae_image_v1/frontend/css/style.css`
Expected: ~350 lines

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/frontend/css/style.css
git commit -m "feat: rewrite CSS with blue-cyan design system for V1 frontend redesign

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Rewrite HTML Structure

**Files:**
- Rewrite: `code/algae_image_v1/frontend/index.html`

- [ ] **Step 1: Write the new index.html**

Write `code/algae_image_v1/frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>藻影卫士 V1.0 — 有害藻华早期预警平台</title>
  <link rel="stylesheet" href="css/style.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
  <main class="app">

    <!-- ═══ Top Bar ═══ -->
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">藻</div>
        <div>
          <h1>藻影卫士 有害藻华早期预警平台</h1>
          <p class="subtitle">偏振暗场显微成像 · YOLO识别计数 · <strong>结构张量偏振</strong></p>
        </div>
      </div>
      <div class="top-actions">
        <div class="status-pill"><i class="status-dot"></i>系统在线</div>
        <button class="btn" id="refreshBtn" onclick="location.reload()">刷新</button>
        <button class="btn btn-primary" id="reportBtn">导出报告</button>
      </div>
    </header>

    <!-- ═══ Navigation ═══ -->
    <nav class="navbar" id="navBar">
      <button class="nav-btn active" data-page="home">首页</button>
      <button class="nav-btn" data-page="detect">检测工具</button>
      <button class="nav-btn" data-page="history">历史记录</button>
      <button class="nav-btn" data-page="dashboard">数据统计</button>
      <button class="nav-btn" data-page="devices" disabled>设备管理</button>
      <button class="nav-btn" data-page="review" disabled>人工复核</button>
    </nav>

    <!-- ═══ Pipeline Bar ═══ -->
    <div class="pipeline-bar" id="pipelineBar">
      <div class="pipe-step" data-pipe="0">
        <span class="num">1</span>
        <div class="info"><strong>偏振暗场采集</strong><small>DoFP相机 · 多角度</small></div>
      </div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step" data-pipe="1">
        <span class="num">2</span>
        <div class="info"><strong>Stokes重建</strong><small>S0/S1/S2 · RDN</small></div>
      </div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step" data-pipe="2">
        <span class="num">3</span>
        <div class="info"><strong>图像增强</strong><small>去散射 · 对比度</small></div>
      </div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step" data-pipe="3">
        <span class="num">4</span>
        <div class="info"><strong>YOLO识别计数</strong><small>分类 · 框选 · 浓度</small></div>
      </div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step" data-pipe="4">
        <span class="num">5</span>
        <div class="info"><strong>融合预警</strong><small>风险分级 · 四级预警</small></div>
      </div>
    </div>

    <!-- ═══ Metrics Cards ═══ -->
    <section class="metrics-row" id="metricsRow">
      <article class="metric-card">
        <span class="metric-label">总检测次数</span>
        <strong class="metric-value" id="metricTotal">--</strong>
        <small class="metric-sub">累计检测样本</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">今日检测</span>
        <strong class="metric-value" id="metricToday">--</strong>
        <small class="metric-sub">当日处理量</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">高危预警</span>
        <strong class="metric-value danger" id="metricHighRisk">--</strong>
        <small class="metric-sub">需立即关注</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">平均质量分</span>
        <strong class="metric-value" id="metricAvgQ">--</strong>
        <small class="metric-sub">Q Score · 图像质量</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">活跃藻种</span>
        <strong class="metric-value" id="metricClassCount">--</strong>
        <small class="metric-sub">检出类别数</small>
      </article>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════
         PAGE: Home Dashboard (default)
         ═══════════════════════════════════════════════════════════════ -->
    <section class="page-panel active" id="page-home">
      <div class="main-layout">
        <!-- Left Panel: Stats + Quick Actions -->
        <aside class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">数据概览</h2>
              <p class="panel-subtitle">实时统计 · 快速操作</p>
            </div>
          </div>
          <div class="stat-list">
            <div class="stat-item">
              <div class="stat-num" id="homeStatTotal">--</div>
              <div class="stat-text">总检测次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-num" id="homeStatToday">--</div>
              <div class="stat-text">今日检测</div>
            </div>
            <div class="stat-item">
              <div class="stat-num" style="color:var(--risk-red);" id="homeStatHighRisk">--</div>
              <div class="stat-text">高危预警</div>
            </div>
          </div>
          <div class="quick-actions">
            <button class="btn btn-primary" onclick="switchPage('detect')" style="width:100%;justify-content:center;padding:12px;">
              开始新检测
            </button>
            <button class="btn" onclick="switchPage('history')" style="width:100%;justify-content:center;">
              查看历史记录
            </button>
          </div>
        </aside>

        <!-- Center Panel: Detection -->
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">快速检测</h2>
              <p class="panel-subtitle">上传藻类显微图像 · 偏振分析 · YOLO识别</p>
            </div>
          </div>
          <div class="panel-body">
            <!-- Upload Zone — IDs preserved for detection.js -->
            <div class="upload-zone" id="uploadZone">
              <span class="upload-icon">🔬</span>
              <p class="upload-text">拖拽图片到此处 或 点击选择文件</p>
              <p class="upload-hint">支持 JPG / PNG / TIFF / BMP 格式，最大 50 张</p>
              <input type="file" id="fileInput" accept="image/jpeg,image/png,image/tiff,.tif,.bmp,image/bmp" multiple hidden>
              <input type="file" id="folderInput" webkitdirectory hidden>
              <img id="previewImage" class="preview-thumb hidden" alt="预览">
            </div>
            <div class="btn-group mt-md">
              <button class="btn btn-outline" id="btnSelectFolder">选择文件夹</button>
              <button class="btn btn-primary" id="btnSingleDetect" disabled>单图检测</button>
              <button class="btn" id="btnBatchDetect" disabled>批量处理</button>
            </div>
            <p class="text-sm text-muted mt-md" id="fileCountLabel"></p>
            <!-- Progress bar — IDs preserved -->
            <div class="progress-bar-wrap" id="progressWrap">
              <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
              <p class="progress-text" id="progressText"></p>
            </div>
            <!-- Result — IDs preserved -->
            <div class="result-panel mt-md" id="resultPanel">
              <div class="panel-header">
                <span>检测结果</span>
                <span class="text-sm text-muted" id="resultTime" style="display:none;"></span>
              </div>
              <div class="panel-body">
                <div class="empty-state" id="resultEmpty">
                  <span class="empty-icon">📆</span>
                  <p class="empty-text">暂无检测结果</p>
                  <p class="empty-hint">请上传图片后点击检测</p>
                </div>
                <div id="resultContent" class="hidden">
                  <img id="resultImage" class="result-image" alt="检测结果">
                  <div class="result-meta" id="resultMeta"></div>
                  <ul class="detect-list" id="detectList"></ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Right Panel: Recent + Placeholders -->
        <aside class="right-panel">
          <!-- Recent Detections -->
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2 class="panel-title">最近检测</h2>
                <p class="panel-subtitle">最新提交的检测记录</p>
              </div>
            </div>
            <div class="recent-list" id="homeRecentList">
              <div class="empty-state"><p class="empty-text">暂无数据</p></div>
            </div>
          </section>

          <!-- Risk Summary (placeholder) -->
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2 class="panel-title">风险摘要</h2>
                <p class="panel-subtitle">四级预警体系</p>
              </div>
            </div>
            <div class="placeholder-section">
              <div style="display:flex;gap:4px;justify-content:center;flex-wrap:wrap;margin-bottom:12px;">
                <span class="risk-badge risk-red">红色·高危</span>
                <span class="risk-badge risk-medium" style="color:var(--risk-orange);background:var(--risk-orange-bg);">橙色·预警</span>
                <span class="risk-badge risk-medium">黄色·注意</span>
                <span class="risk-badge risk-low">绿色·低风险</span>
              </div>
              <p class="ph-desc">
                红色：有害藻华爆发，需立即应急处置<br>
                橙色：藻密度快速上升，建议现场确认<br>
                黄色：指标抬升，增加采样频率<br>
                绿色：处于背景水平，正常监测
              </p>
            </div>
          </section>

          <!-- Data Loop (placeholder) -->
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2 class="panel-title">数据闭环</h2>
                <p class="panel-subtitle">采集 → 识别 → 复核 → 再训练</p>
              </div>
            </div>
            <div class="loop-flow">
              <div class="loop-node done">
                <span class="dot">✓</span><label>采集</label>
                <small style="color:var(--muted);">偏振暗场成像</small>
              </div>
              <div class="loop-node done">
                <span class="dot">✓</span><label>识别</label>
                <small style="color:var(--muted);">YOLO分类计数</small>
              </div>
              <div class="loop-node">
                <span class="dot">3</span><label>复核</label>
                <small style="color:var(--muted);">等待专家确认</small>
              </div>
              <div class="loop-node">
                <span class="dot">4</span><label>再训练</label>
                <small style="color:var(--muted);">待加入样本池</small>
              </div>
            </div>
            <div class="placeholder-section" style="padding-top:8px;">
              <p class="ph-desc">人工复核与增量训练功能将在后续版本开放</p>
            </div>
          </section>
        </aside>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════
         PAGE: Detection (dedicated page — same upload zone + result)
         ═══════════════════════════════════════════════════════════════ -->
    <section class="page-panel" id="page-detect">
      <div class="page-inner">
        <div class="main-layout" style="grid-template-columns:1fr;">
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2 class="panel-title">检测工具</h2>
                <p class="panel-subtitle">上传藻类显微图像进行分析</p>
              </div>
            </div>
            <div class="panel-body">
              <p class="text-sm text-muted mb-md">请使用首页进行检测操作，或在此查看当前检测结果。</p>
              <button class="btn btn-primary" onclick="switchPage('home')">返回首页检测</button>
            </div>
          </section>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════
         PAGE: History
         ═══════════════════════════════════════════════════════════════ -->
    <section class="page-panel" id="page-history">
      <div class="page-inner">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th><th>文件名</th><th>风险等级</th><th>检测数量</th><th>质量评分</th><th>操作</th>
              </tr>
            </thead>
            <tbody id="historyTableBody">
              <tr><td colspan="6">
                <div class="empty-state">
                  <span class="empty-icon">📄</span>
                  <p class="empty-text">暂无检测记录</p>
                  <p class="empty-hint">完成检测后记录将显示在此处</p>
                </div>
              </td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination" id="historyPagination"></div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════
         PAGE: Dashboard / Stats
         ═══════════════════════════════════════════════════════════════ -->
    <section class="page-panel" id="page-dashboard">
      <div class="page-inner">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value" id="statTotal">--</div>
            <div class="stat-label">总检测次数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="statToday">--</div>
            <div class="stat-label">今日检测</div>
          </div>
          <div class="stat-card">
            <div class="stat-value high-risk" id="statHighRisk">--</div>
            <div class="stat-label">高危预警</div>
          </div>
        </div>
        <div class="charts-grid">
          <div class="chart-card">
            <div class="chart-title">藻类分布</div>
            <canvas id="chartClassDist"></canvas>
          </div>
          <div class="chart-card">
            <div class="chart-title">风险分布</div>
            <canvas id="chartRiskDist"></canvas>
          </div>
        </div>
        <div style="margin-top:var(--spacing-lg);">
          <div class="chart-card">
            <div class="chart-title">最近检测记录</div>
            <div id="recentDetections" style="padding:8px;"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════
         PAGE: Devices (placeholder)
         ═══════════════════════════════════════════════════════════════ -->
    <section class="page-panel" id="page-devices">
      <div class="page-inner">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">设备管理</h2>
              <p class="panel-subtitle">偏振相机 · 暗场光源 · 运维状态</p>
            </div>
          </div>
          <div class="placeholder-section">
            <span class="ph-icon">⚙</span>
            <p class="ph-title">设备管理模块将在后续版本开放</p>
            <p class="ph-desc">届时支持：DoFP偏振相机状态监控 · 暗场光源校准 · 成像窗口清洁度检测 · 网络链路诊断</p>
          </div>
          <div style="padding:0 16px 16px;display:grid;gap:10px;max-width:400px;margin:0 auto;">
            <div class="recent-item">
              <span>偏振相机</span>
              <div class="progress-bar" style="width:96px;"><div class="progress-fill" style="width:100%;background:var(--risk-green);"></div></div>
            </div>
            <div class="recent-item">
              <span>暗场光源</span>
              <div class="progress-bar" style="width:96px;"><div class="progress-fill" style="width:100%;background:var(--risk-green);"></div></div>
            </div>
            <div class="recent-item">
              <span>网络链路</span>
              <div class="progress-bar" style="width:96px;"><div class="progress-fill" style="width:100%;background:var(--risk-green);"></div></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════
         PAGE: Review (placeholder)
         ═══════════════════════════════════════════════════════════════ -->
    <section class="page-panel" id="page-review">
      <div class="page-inner">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">人工复核</h2>
              <p class="panel-subtitle">专家确认 · 标注修正 · 加入训练集</p>
            </div>
          </div>
          <div class="placeholder-section">
            <span class="ph-icon">✓</span>
            <p class="ph-title">人工复核模块将在后续版本开放</p>
            <p class="ph-desc">届时支持：低置信度样本专家确认 · 误检/漏检标注修正 · 样本加入增量训练池 · 复核历史追踪</p>
          </div>
          <div class="loop-flow" style="max-width:500px;margin:0 auto 16px;">
            <div class="loop-node done"><span class="dot">✓</span><label>采集</label><small style="color:var(--muted);">偏振成像</small></div>
            <div class="loop-node done"><span class="dot">✓</span><label>识别</label><small style="color:var(--muted);">YOLO检测</small></div>
            <div class="loop-node"><span class="dot">3</span><label>复核</label><small style="color:var(--muted);">专家确认</small></div>
            <div class="loop-node"><span class="dot">4</span><label>再训练</label><small style="color:var(--muted);">增量更新</small></div>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- ═══ Report Modal ═══ -->
  <div class="modal" id="reportModal" role="dialog" aria-modal="true">
    <div class="modal-card">
      <h2>藻影卫士监测报告摘要</h2>
      <p id="reportText"></p>
      <p id="reportSuggestion" style="padding:8px 12px;background:rgba(25,118,210,.06);border-radius:6px;border:1px solid rgba(25,118,210,.15);"></p>
      <button class="btn btn-primary" id="closeModal">关闭</button>
    </div>
  </div>

  <!-- ═══ Scripts ═══ -->
  <script src="js/detection.js"></script>
  <script src="js/dashboard.js"></script>
  <script src="js/app.js"></script>
  <script src="js/dashboard-home.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify all critical element IDs are present**

Run the following check:
```bash
cd e:/code/codex/code/algae_image_v1/frontend && grep -oP 'id="[^"]*"' index.html | sort
```
Expected output must include all IDs referenced by detection.js and dashboard.js:
`uploadZone`, `fileInput`, `folderInput`, `btnSelectFolder`, `btnSingleDetect`, `btnBatchDetect`, `fileCountLabel`, `previewImage`, `progressWrap`, `progressFill`, `progressText`, `resultEmpty`, `resultContent`, `resultImage`, `resultMeta`, `detectList`, `resultTime`, `statTotal`, `statToday`, `statHighRisk`, `chartClassDist`, `chartRiskDist`, `recentDetections`, `historyTableBody`, `historyPagination`, `resultPanel`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/frontend/index.html
git commit -m "feat: rewrite HTML with dashboard layout and all panels

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Modify app.js — Add Pipeline Functions, Navigation, and Dashboard Init

**Files:**
- Modify: `code/algae_image_v1/frontend/js/app.js`

The existing `app.js` has tab-switching logic (`initTabs`, `switchTab`). We replace this with page-switching logic, add pipeline animation functions, and add dashboard homepage initialization. All existing utility functions (`formatTime`, `showToast`, `toggleVisibility`, `setHTML`, `apiRequest`) are preserved unchanged.

- [ ] **Step 1: Write the updated app.js**

Write `code/algae_image_v1/frontend/js/app.js`:

```js
/**
 * Algae Guardian V1.0 — Main Application
 * Navigation, pipeline animation, shared utilities, report modal.
 */

const API = '/api/v1';

// ── State ──────────────────────────────────────────────────────────────────
var currentPage = 'home';
var currentTab = 'home';  // backward compat for detection.js
var currentHistoryPage = 1;
var currentHistoryDetailId = null;

// ── DOM Ready ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  initNavigation();
  initReportModal();
  loadHomeMetrics();
});

// ── Navigation ─────────────────────────────────────────────────────────────
function initNavigation() {
  document.querySelectorAll('#navBar .nav-btn:not([disabled])').forEach(function (btn) {
    btn.addEventListener('click', function () {
      switchPage(btn.getAttribute('data-page'));
    });
  });
}

// Backward compat for detection.js (viewHistoryDetail calls switchTab)
function switchTab(pageName) {
  // Map old tab names to new page names
  var map = { detect: 'home', history: 'history', dashboard: 'dashboard' };
  switchPage(map[pageName] || pageName);
}

function switchPage(pageName) {
  if (currentPage === pageName) return;
  currentPage = pageName;
  currentTab = pageName;  // sync backward-compat var for detection.js

  // Update nav button states
  document.querySelectorAll('#navBar .nav-btn').forEach(function (btn) {
    btn.classList.toggle('active', btn.getAttribute('data-page') === pageName);
  });

  // Show/hide page panels
  document.querySelectorAll('.page-panel').forEach(function (panel) {
    panel.classList.toggle('active', panel.id === 'page-' + pageName);
  });

  // Show/hide main-layout sections (only for home page)
  var mainLayout = document.querySelector('.main-layout');
  if (mainLayout) {
    mainLayout.style.display = (pageName === 'home') ? '' : 'none';
  }

  // Page-specific loading
  if (pageName === 'dashboard' || pageName === 'home') {
    loadDashboard();
  }
  if (pageName === 'history') {
    loadHistory(currentHistoryPage);
  }
}

// ── Pipeline Animation ─────────────────────────────────────────────────────
var _pipelineTimer = null;

function updatePipeline(activeIndex) {
  document.querySelectorAll('.pipe-step').forEach(function (step, i) {
    step.classList.toggle('active', i === activeIndex);
    step.classList.toggle('done', i < activeIndex);
  });
}

function completePipeline() {
  document.querySelectorAll('.pipe-step').forEach(function (step) {
    step.classList.add('done');
    step.classList.remove('active');
  });
}

function resetPipeline() {
  document.querySelectorAll('.pipe-step').forEach(function (step) {
    step.classList.remove('active', 'done');
  });
  if (_pipelineTimer) {
    clearInterval(_pipelineTimer);
    _pipelineTimer = null;
  }
}

// ── Homepage Metrics ───────────────────────────────────────────────────────
async function loadHomeMetrics() {
  try {
    var data = await apiRequest('/dashboard/stats');

    // Top metrics row
    document.getElementById('metricTotal').textContent = (data.total_detections !== undefined ? data.total_detections : '--');
    document.getElementById('metricToday').textContent = (data.today_count !== undefined ? data.today_count : '--');
    var riskDist = data.risk_distribution || {};
    document.getElementById('metricHighRisk').textContent = (riskDist.high !== undefined ? riskDist.high : '--');

    // Average Q score
    var recent = data.recent_detections || [];
    if (recent.length > 0) {
      var sumQ = 0, countQ = 0;
      recent.forEach(function (r) {
        if (r.q_score !== undefined && r.q_score !== null) { sumQ += r.q_score; countQ++; }
      });
      document.getElementById('metricAvgQ').textContent = countQ > 0 ? (sumQ / countQ).toFixed(2) : '--';
    } else {
      document.getElementById('metricAvgQ').textContent = '--';
    }

    // Active class count
    var classDist = data.class_distribution || {};
    var classKeys = Object.keys(classDist);
    document.getElementById('metricClassCount').textContent = classKeys.length || '--';

    // Left panel stats
    document.getElementById('homeStatTotal').textContent = (data.total_detections !== undefined ? data.total_detections : '--');
    document.getElementById('homeStatToday').textContent = (data.today_count !== undefined ? data.today_count : '--');
    document.getElementById('homeStatHighRisk').textContent = (riskDist.high !== undefined ? riskDist.high : '--');

    // Right panel: recent detections
    renderHomeRecent(recent);

  } catch (err) {
    console.error('Load home metrics failed:', err);
  }
}

function renderHomeRecent(recent) {
  var container = document.getElementById('homeRecentList');
  if (!container) return;

  if (!recent || recent.length === 0) {
    container.innerHTML = '<div class="empty-state"><p class="empty-text">暂无数据</p></div>';
    return;
  }

  container.innerHTML = recent.slice(0, 5).map(function (item) {
    var riskLevel = item.risk_level || 'low';
    var riskLabel = (typeof RISK_LABELS !== 'undefined' ? RISK_LABELS[riskLevel] : riskLevel) || riskLevel;
    var qScore = item.q_score !== undefined && item.q_score !== null
      ? (typeof item.q_score === 'number' ? item.q_score.toFixed(2) : item.q_score)
      : '--';
    var filename = item.filename || '未知文件';
    return '<div class="recent-item">' +
      '<span class="recent-name" title="' + escapeHtml(filename) + '">' + escapeHtml(filename) + '</span>' +
      '<span style="font-family:var(--font-mono);font-size:12px;">Q=' + qScore + '</span>' +
      '<span class="risk-badge risk-' + riskLevel + '">' + riskLabel + '</span>' +
      '<span style="font-size:11px;color:var(--muted);">' + formatTime(item.created_at || item.timestamp || item.detect_time) + '</span>' +
      '</div>';
  }).join('');
}

// ── Report Modal ───────────────────────────────────────────────────────────
function initReportModal() {
  document.getElementById('reportBtn').addEventListener('click', function () {
    var totalEl = document.getElementById('metricTotal');
    var highRiskEl = document.getElementById('metricHighRisk');
    var todayEl = document.getElementById('metricToday');
    var total = totalEl ? totalEl.textContent : '--';
    var highRisk = highRiskEl ? highRiskEl.textContent : '--';
    var today = todayEl ? todayEl.textContent : '--';

    document.getElementById('reportText').textContent =
      '藻影卫士 V1.0 当前监测状态：累计检测 ' + total + ' 次，今日 ' + today + ' 次，' +
      '高危预警 ' + highRisk + ' 条。系统基于结构张量偏振模拟 + RDN偏振重建 + YOLOv8s检测管线运行。';
    document.getElementById('reportSuggestion').textContent =
      '建议：持续监控藻密度变化趋势，对高危样本及时复核确认。定期检查模型性能，必要时触发增量再训练。';
    document.getElementById('reportModal').classList.add('show');
  });

  document.getElementById('closeModal').addEventListener('click', function () {
    document.getElementById('reportModal').classList.remove('show');
  });
  document.getElementById('reportModal').addEventListener('click', function (event) {
    if (event.target.id === 'reportModal') {
      document.getElementById('reportModal').classList.remove('show');
    }
  });
}

// ── Utilities ──────────────────────────────────────────────────────────────

function formatTime(ts) {
  if (!ts) return '--';
  var num = typeof ts === 'string' ? parseInt(ts, 10) : ts;
  if (num < 1e12) num = num * 1000;
  var d = new Date(num);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration || 3000;
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(function () {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, duration);
}

function toggleVisibility(el, show) {
  if (typeof el === 'string') el = document.getElementById(el);
  if (!el) return;
  if (show) { el.classList.remove('hidden'); }
  else { el.classList.add('hidden'); }
}

function setHTML(id, html) {
  var el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

async function apiRequest(url, options) {
  var opts = options || {};
  try {
    var response = await fetch(API + url, opts);
    if (!response.ok) {
      var errorBody = '';
      try { errorBody = await response.text(); } catch (e) {}
      throw new Error('HTTP ' + response.status + ': ' + (errorBody || response.statusText));
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('无法连接到后端服务，请确认服务器已启动 (localhost:8000)');
    }
    throw err;
  }
}
```

- [ ] **Step 2: Verify the file saves without syntax errors**

Run: `node --check e:/code/codex/code/algae_image_v1/frontend/js/app.js`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/frontend/js/app.js
git commit -m "feat: update app.js with navigation, pipeline, metrics, and report modal

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Minor Edit to dashboard.js — Remove Broken statAvgQ / statClassCount References

**Files:**
- Modify: `code/algae_image_v1/frontend/js/dashboard.js:33-36`

The old `statAvgQ` and `statClassCount` elements no longer exist in the new HTML (replaced by `metricAvgQ` and `metricClassCount` in the top metrics row). We remove those two blocks from `loadDashboard()` since the new `app.js` handles metrics rendering via `loadHomeMetrics()`.

- [ ] **Step 1: Remove the stale statAvgQ and statClassCount code**

In `code/algae_image_v1/frontend/js/dashboard.js`, find and remove lines 33-37 (the `statAvgQ` setter block):

```js
    // Average Q score from recent detections
    var recent = data.recent_detections || [];
    if (recent.length > 0) {
      var sumQ = 0, countQ = 0;
      recent.forEach(function (r) {
        if (r.q_score !== undefined && r.q_score !== null) { sumQ += r.q_score; countQ++; }
      });
      document.getElementById('statAvgQ').textContent = countQ > 0 ? (sumQ / countQ).toFixed(2) : '--';
    } else {
      document.getElementById('statAvgQ').textContent = '--';
    }
```

And lines 39-41 (the `statClassCount` setter block):

```js
    // Active class count
    var classDist = data.class_distribution || {};
    var classKeys = Object.keys(classDist);
    document.getElementById('statClassCount').textContent = classKeys.length || '--';
```

Replace both blocks with nothing (simply delete them). The `recent` variable extraction on line 26 and the `classDist` extraction on line 38 should also be removed if they cause unused variable warnings, but they're harmless to keep.

The corrected `loadDashboard()` function should look like this after the edit:

```js
async function loadDashboard() {
  try {
    var data = await apiRequest('/dashboard/stats');

    // Update stat cards (3 metrics on dashboard sub-page)
    document.getElementById('statTotal').textContent = (data.total_detections !== undefined ? data.total_detections : '--');
    document.getElementById('statToday').textContent = (data.today_count !== undefined ? data.today_count : '--');

    var riskDist = data.risk_distribution || {};
    document.getElementById('statHighRisk').textContent = (riskDist.high !== undefined ? riskDist.high : '--');

    // Render charts
    renderClassDistribution(data.class_distribution || {});
    renderRiskDistribution(riskDist);

    // Render recent detections
    renderRecentDetections(data.recent_detections || []);

  } catch (err) {
    showToast('加载仪表板失败: ' + err.message, 'error');
    console.error(err);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v1/frontend/js/dashboard.js
git commit -m "fix: remove stale statAvgQ/statClassCount references from dashboard.js

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Create dashboard-home.js (Stub)

**Files:**
- Create: `code/algae_image_v1/frontend/js/dashboard-home.js`

This file is a minimal stub since most homepage rendering logic is already in `app.js` (`loadHomeMetrics`, `renderHomeRecent`). The file exists as a placeholder for future dashboard-specific features (auto-refresh, WebSocket integration, etc.).

- [ ] **Step 1: Write the stub file**

Write `code/algae_image_v1/frontend/js/dashboard-home.js`:

```js
/**
 * Algae Guardian V1.0 — Dashboard Homepage Module
 * Homepage-specific rendering and refresh logic.
 * Core metrics rendering is in app.js (loadHomeMetrics).
 */

// ── Auto-refresh (every 60s when home page is active) ──────────────────────
var _homeRefreshInterval = null;

function startHomeAutoRefresh() {
  if (_homeRefreshInterval) return;
  _homeRefreshInterval = setInterval(function () {
    if (currentPage === 'home') {
      loadHomeMetrics();
    }
  }, 60000);
}

function stopHomeAutoRefresh() {
  if (_homeRefreshInterval) {
    clearInterval(_homeRefreshInterval);
    _homeRefreshInterval = null;
  }
}

// Start auto-refresh on load
document.addEventListener('DOMContentLoaded', function () {
  startHomeAutoRefresh();
});
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v1/frontend/js/dashboard-home.js
git commit -m "feat: add dashboard-home.js with auto-refresh for homepage metrics

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Integration — Verify the App Starts and Functions Correctly

- [ ] **Step 1: Start the backend server**

```bash
cd e:/code/codex/code/algae_image_v1 && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
```
Wait 3 seconds for server to start.

- [ ] **Step 2: Verify frontend loads without JS errors**

Open `http://localhost:8000/app/` in a browser. Open browser console (F12) and check for errors.

Expected: No red console errors. The dashboard homepage should render with:
- Blue-cyan top bar with brand and action buttons
- 6-item navigation bar (首页 active, 设备管理/人工复核 disabled)
- 5-step pipeline bar (all steps inactive/neutral)
- 5 metrics cards across top (may show "--" if no data)
- 3-column layout: left stats panel, center upload zone, right panels

- [ ] **Step 3: Test navigation**

Click "历史记录" in the nav bar.
Expected: History page shows with empty state "暂无检测记录".

Click "数据统计" in the nav bar.
Expected: Dashboard page shows with 3 stat cards and 2 chart containers.

Click "首页" to return.
Expected: Dashboard homepage shows again.

- [ ] **Step 4: Test navigation to placeholder pages**

Click "设备管理" — should be disabled (gray, not clickable).
Click "人工复核" — should be disabled (gray, not clickable).

- [ ] **Step 5: Test report modal**

Click "导出报告" button.
Expected: Modal opens with report summary text and close button.
Click "关闭" or backdrop.
Expected: Modal closes.

- [ ] **Step 6: Test detection flow (requires backend)**

Upload an image via the upload zone on the homepage.
Click "单图检测".
Expected: Pipeline bar animates through 5 steps, result appears in the result panel below the upload zone.

- [ ] **Step 7: Commit if all tests pass**

```bash
git add -A
git commit -m "test: verify V1 frontend redesign integration — all pages load, nav works, detection functions

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Plan Summary

| Task | Files | Est. Time |
|------|-------|-----------|
| 1. Rewrite CSS | `style.css` | 3 min |
| 2. Rewrite HTML | `index.html` | 5 min |
| 3. Modify app.js | `app.js` | 5 min |
| 4. Minor dashboard.js edit | `dashboard.js` | 2 min |
| 5. Create dashboard-home.js | `dashboard-home.js` (new) | 2 min |
| 6. Integration test | All | 5 min |
| **Total** | | **~22 min** |
