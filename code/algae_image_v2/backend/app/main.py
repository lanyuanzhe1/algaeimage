"""Algae Image V2 — FMPD HSV Pipeline — FastAPI Application Entry Point."""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = sys._MEIPASS
else:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.app.config import DATA_DIR, HOST, PORT, RDN_WEIGHTS, RESULT_DIR, UPLOAD_DIR, resource_path
from backend.app.database import init_db

pipeline_runner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline_runner

    await init_db()
    print(f"[Startup] Database initialised at {DATA_DIR}")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Startup] Device: {device}")

    # V2: Structure Tensor pipeline — load RDN + YOLO
    from backend.app.services.pipeline import PipelineRunner
    from core_engine.reconstructor import load_rdn_model

    rdn_model = None
    if os.path.exists(RDN_WEIGHTS):
        rdn_model = load_rdn_model(RDN_WEIGHTS, device)
        print(f"[Startup] RDN loaded from {RDN_WEIGHTS}")
    else:
        print(f"[Startup] RDN weights not found at {RDN_WEIGHTS} — running without RDN")

    pipeline_runner = PipelineRunner.create(device=device, rdn_model=rdn_model)
    print(f"[Startup] Pipeline ready — Algae Image V2 (StructTensor+RDN, FMPD 5-class)")

    # Init camera controller (lazy — won't open device until /stream/start)
    try:
        from backend.app.services.camera import camera_controller
        camera_controller.configure(pipeline_runner, os.path.join(RESULT_DIR, "live"))
        app.state.camera_controller = camera_controller
        print("[Startup] Camera controller ready")
    except Exception as e:
        print(f"[Startup] Camera SDK not available (non-Windows or MVS not installed): {e}")
        app.state.camera_controller = None

    # Init video controller (always available — no SDK needed)
    from backend.app.services.video import video_controller
    video_controller.configure(pipeline_runner, os.path.join(RESULT_DIR, "live"))
    app.state.video_controller = video_controller
    print("[Startup] Video controller ready")

    yield

    # Shutdown camera if running
    if app.state.camera_controller:
        app.state.camera_controller.finalize()
        print("[Shutdown] Camera controller released")

    # Shutdown video if running
    if app.state.video_controller and app.state.video_controller.is_active():
        app.state.video_controller.stop()
        print("[Shutdown] Video controller released")

    pipeline_runner = None
    print("[Shutdown] Models released")


app = FastAPI(
    title="Algae Image V2",
    description="FMPD bright-field algae detection — HSV polarization + YOLO",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.app.routes import router as detect_router
from backend.app.routes_data import router as data_router

app.include_router(detect_router)
app.include_router(data_router)

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
_live_dir = os.path.join(RESULT_DIR, "live")
os.makedirs(_live_dir, exist_ok=True)
app.mount("/static/results", StaticFiles(directory=RESULT_DIR), name="results")
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static/live", StaticFiles(directory=_live_dir), name="live")

FRONTEND_DIR = resource_path("frontend")
# In dev mode, serve the Vite build output (frontend/dist)
_dist = os.path.join(FRONTEND_DIR, "dist")
if os.path.isdir(_dist):
    FRONTEND_DIR = _dist
if not os.path.isdir(FRONTEND_DIR):
    raise RuntimeError(f"Frontend directory not found: {FRONTEND_DIR} (build with: cd frontend && npm run build)")
# Serve frontend: assets at /assets, SPA fallback at /app/*
_assets_dir = os.path.join(FRONTEND_DIR, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

from fastapi.responses import FileResponse
_index_html = os.path.join(FRONTEND_DIR, "index.html")
@app.get("/app/{full_path:path}")
async def app_spa_fallback(full_path: str):
    """SPA fallback: serve index.html for any client-side route."""
    if os.path.isfile(_index_html):
        return FileResponse(_index_html)
    return {"detail": "Not Found"}

@app.get("/app")
async def app_root():
    """Serve index.html at /app root."""
    if os.path.isfile(_index_html):
        return FileResponse(_index_html)
    return {"detail": "Not Found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
