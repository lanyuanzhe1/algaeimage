---
paths: code/algae_image_v1/backend/**;code/algae_image_v2/backend/**
---

# Backend Rules

## Architecture

- **Thin orchestration layer.** No business logic in backend — all logic lives in `core_engine/`.
- **FastAPI with `lifespan` async context manager** — NOT the deprecated `on_event`.
- **SQLite + aiosqlite** — async database access. `init_db()` auto-creates tables on startup.

## Structure

```
backend/app/
  main.py              ← FastAPI app, lifespan, mount static files
  config.py            ← All paths, weights, risk thresholds centralized here
  database.py          ← SQLite init + connection
  schemas.py           ← Pydantic models for request/response
  routes/
    detection.py       ← POST /api/v1/detect, /detect/batch
    dashboard.py       ← GET /api/v1/dashboard/stats
    history.py         ← GET/POST/DELETE /api/v1/history
  services/
    pipeline.py        ← PipelineRunner class orchestrates 5-stage pipeline
```

## Key patterns

- `PipelineRunner` in `services/pipeline.py` is the central orchestrator. It imports from `core_engine/`, never the reverse.
- Routes delegate to `PipelineRunner` methods. Routes never import numpy/torch/cv2 directly.
- Config values come from `config.py`, never hardcoded in routes.
- Batch detection capped at 50 images.
- All endpoints prefixed `/api/v1/`.

## NEVER

- Import FastAPI, SQLite, or Pydantic in `core_engine/`
- Put business logic (image processing, ML inference) in route handlers
- Use synchronous SQLite — always `aiosqlite`
- Hardcode paths or thresholds — use `config.py`
