"""Algae Guardian Backend - FastAPI Application.

Low-cost underwater polarization microscopic intelligent monitoring system
for harmful algal bloom early warning.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import HOST, PORT, CORS_ORIGINS, RESULTS_DIR, UPLOAD_DIR
from .database import init_db
from .routes import detection, devices, dashboard, review

# Create static/results directories
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "results").mkdir(exist_ok=True)
(STATIC_DIR / "uploads").mkdir(exist_ok=True)

# Frontend and image directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIR.mkdir(exist_ok=True)
PIC_DIR = PROJECT_ROOT.parent.parent / "pic"  # e:/code/codex/pic/
PIC_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Algae Guardian API",
    description="Low-cost underwater polarization microscopic monitoring system for harmful algal bloom early warning",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
app.mount("/pic", StaticFiles(directory=str(PIC_DIR), html=False), name="pic")

# Register routers
app.include_router(detection.router)
app.include_router(devices.router)
app.include_router(dashboard.router)
app.include_router(review.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    return {
        "name": "Algae Guardian",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
