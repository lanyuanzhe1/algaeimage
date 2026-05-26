"""Application configuration constants."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
YOLO_WEIGHTS = os.path.join(WEIGHTS_DIR, "best_v8l.pt")
YOLO_WEIGHTS_V8S = os.path.join(WEIGHTS_DIR, "best_v8s.pt")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RESULT_DIR = os.path.join(DATA_DIR, "results")
DB_PATH = os.path.join(DATA_DIR, "history.db")

API_PREFIX = "/api/v1"
HOST = "0.0.0.0"
PORT = 8000
