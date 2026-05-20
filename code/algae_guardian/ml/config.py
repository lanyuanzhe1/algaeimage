"""ML module configuration."""
from pathlib import Path
import os

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
ML_DIR = PROJECT_ROOT / "ml"
MODELS_DIR = ML_DIR / "models"
DATA_DIR = PROJECT_ROOT / "backend" / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"

# Ensure directories exist
for d in [MODELS_DIR, UPLOAD_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# YOLO Settings
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", str(MODELS_DIR / "algae_detection.pt"))
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5"))
YOLO_IOU_THRESHOLD = float(os.getenv("YOLO_IOU_THRESHOLD", "0.45"))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "cpu")
YOLO_IMG_SIZE = int(os.getenv("YOLO_IMG_SIZE", "640"))

# Algae class definitions — aligned with trained YOLOv8l model (best.pt)
# Training: FMPD 293 images, mAP50=0.429, 5 classes
ALGAE_CLASSES = {
    0: {"name": "Other-phytoplankton", "label": "其他藻类", "risk": "medium", "toxicity": False},
    1: {"name": "Non-phytoplankton",   "label": "非藻类",   "risk": "low",   "toxicity": False},
    2: {"name": "Woronichinia",        "label": "沃罗藻",   "risk": "high",  "toxicity": True},
    3: {"name": "Spiroides",           "label": "卷曲鱼腥藻", "risk": "high", "toxicity": True},
    4: {"name": "Dinobryon",           "label": "锥囊藻",   "risk": "medium","toxicity": False},
}

# Sampling volume (mm³) = FoV area (mm²) × depth (mm)
FOV_AREA_MM2 = 1.0  # 1 mm × 1 mm
DEPTH_MM = 1.0
SAMPLE_VOLUME_UL = (FOV_AREA_MM2 * DEPTH_MM) / 1000  # mm³ → μL

# Risk thresholds (cells/μL)
RISK_THRESHOLDS = {
    "low": {"max": 100},
    "medium": {"max": 500},
    "high": {"max": 2000},
    "critical": {"max": float("inf")},
}

# Environment factor risk weights
TEMP_RANGE = (28, 34)       # °C - optimal algae growth range
SALINITY_RANGE = (22, 28)   # psu
PH_RANGE = (7.5, 9.0)
