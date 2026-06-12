"""Application configuration constants."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
RDN_WEIGHTS = os.path.join(WEIGHTS_DIR, "rdn_polarization.pth")
YOLO_WEIGHTS = os.path.join(WEIGHTS_DIR, "best.pt")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RESULT_DIR = os.path.join(DATA_DIR, "results")
DB_PATH = os.path.join(DATA_DIR, "history.db")

API_PREFIX = "/api/v1"
HOST = "0.0.0.0"
PORT = 8000
