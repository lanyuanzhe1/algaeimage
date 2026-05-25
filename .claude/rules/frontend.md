---
paths: code/algae_image_v1/frontend/**
---

# Frontend Rules

## Stack constraints

- **No framework, no build tools.** Pure HTML/CSS/JS. No React, Vue, npm, webpack, TypeScript.
- **Chart.js 4.4.0 via CDN** — the only external dependency. Use `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0">`.
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
- Error display: inline status messages in DOM, not `alert()`.
- Tab state: track active tab via `data-tab` attributes, show/hide sections.

## NEVER

- Add npm/node_modules/package.json to frontend/
- Use React, Vue, Angular, or any SPA framework
- Add a CSS framework (no Tailwind, Bootstrap) — custom CSS only
- Use inline styles or `<style>` blocks in HTML — all CSS in `style.css`
