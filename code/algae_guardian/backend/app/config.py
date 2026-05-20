"""Backend application configuration."""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
STATIC_DIR = BACKEND_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
RESULTS_DIR = STATIC_DIR / "results"
DB_PATH = BACKEND_DIR / "data" / "algae_guardian.db"

for d in [UPLOAD_DIR, RESULTS_DIR, BACKEND_DIR / "data"]:
    d.mkdir(parents=True, exist_ok=True)

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Risk levels
RISK_LEVELS = ["green", "yellow", "orange", "red"]
