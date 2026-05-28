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

from backend.app.config import DATA_DIR, HOST, PORT, RESULT_DIR, UPLOAD_DIR
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

    # V2: no RDN — load YOLO directly via PipelineRunner factory
    from backend.app.services.pipeline import PipelineRunner
    pipeline_runner = PipelineRunner.create(device=device)
    print(f"[Startup] Pipeline ready — Algae Image V2 (HSV, FMPD 5-class)")

    yield

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

from backend.app.routes.detection import router as detect_router
from backend.app.routes.dashboard import router as dashboard_router
from backend.app.routes.history import router as history_router

app.include_router(detect_router)
app.include_router(dashboard_router)
app.include_router(history_router)

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static/results", StaticFiles(directory=RESULT_DIR), name="results")
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

if getattr(sys, 'frozen', False):
    _FRONTEND = os.path.join(sys._MEIPASS, "frontend")
else:
    _FRONTEND = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
FRONTEND_DIR = os.path.normpath(os.path.abspath(_FRONTEND))
if not os.path.isdir(FRONTEND_DIR):
    raise RuntimeError(f"Frontend directory not found: {FRONTEND_DIR}")
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
