"""Algae Guardian V1.0 -- FastAPI Application Entry Point."""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure the project root is on sys.path so core_engine is importable
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.app.config import DATA_DIR, HOST, PORT, RDN_WEIGHTS, YOLO_WEIGHTS, RESULT_DIR, UPLOAD_DIR
from backend.app.database import init_db

# ── Global pipeline runner (populated at startup) ──────────────────────────
pipeline_runner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB, load models.  Shutdown: release resources."""
    global pipeline_runner

    # 1. Database + directories
    await init_db()
    print(f"[Startup] Database initialised at {DATA_DIR}")

    # 2. Detect device
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Startup] Device: {device}")

    # 3. Load RDN
    from core_engine.reconstructor import load_rdn_model
    print(f"[Startup] Loading RDN from {RDN_WEIGHTS}")
    rdn = load_rdn_model(RDN_WEIGHTS, device=device)
    print("[Startup] RDN loaded")

    # 4. Load YOLO
    from core_engine.inference import load_yolo
    print(f"[Startup] Loading YOLO from {YOLO_WEIGHTS}")
    yolo = load_yolo(YOLO_WEIGHTS, device=device)
    print("[Startup] YOLO loaded")

    # 5. Build pipeline runner
    from backend.app.services.pipeline import PipelineRunner
    pipeline_runner = PipelineRunner(rdn, yolo, device=device)
    print("[Startup] Pipeline ready -- Algae Guardian V1.0")

    yield  # ── application runs here ──

    # Shutdown
    pipeline_runner = None
    print("[Shutdown] Models released")


app = FastAPI(
    title="Algae Guardian V1.0",
    description="Polarisation microscopy algae intelligent detection system",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ────────────────────────────────────────────────────────────
from backend.app.routes.detection import router as detect_router
from backend.app.routes.dashboard import router as dashboard_router
from backend.app.routes.history import router as history_router

app.include_router(detect_router)
app.include_router(dashboard_router)
app.include_router(history_router)

# ── Static file mounts ─────────────────────────────────────────────────────
# Ensure directories exist (init_db also creates them, but mounts run at import time)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static/results", StaticFiles(directory=RESULT_DIR), name="results")
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── Frontend SPA mount ─────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if not os.path.isdir(FRONTEND_DIR):
    raise RuntimeError(
        f"Frontend directory not found: {FRONTEND_DIR}\n"
        f"Ensure the frontend/ directory exists with index.html before starting."
    )
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
