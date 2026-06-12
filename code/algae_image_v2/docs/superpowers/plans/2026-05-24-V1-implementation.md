# 藻影卫士 V1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-machine desktop tool that runs the complete algae detection pipeline (RGB → polarization sim → RDN reconstruct → I_enh v2 enhance → YOLOv8s detect) with a browser-based UI.

**Architecture:** Three-layer: `core_engine/` (pure Python, zero framework deps) → `backend/` (FastAPI thin layer, routes + pipeline orchestrator) → `frontend/` (vanilla HTML/CSS/JS, 5-tab SPA). Weights in `weights/`, one-click start via `run.bat`.

**Tech Stack:** Python 3.10+, FastAPI, PyTorch, Ultralytics YOLO, SQLite+aiosqlite, vanilla JS+Chart.js CDN

**Source of truth:** `code/algae_image_v1/docs/V1_design_spec.md`

---

### Task 0: Directory Scaffolding + Requirements

**Files:**
- Create: `code/algae_image_v1/requirements.txt`
- Create: `code/algae_image_v1/backend/__init__.py`
- Create: `code/algae_image_v1/backend/app/__init__.py`
- Create: `code/algae_image_v1/backend/app/routes/__init__.py`
- Create: `code/algae_image_v1/backend/app/services/__init__.py`
- Create: `code/algae_image_v1/core_engine/__init__.py`
- Create: `code/algae_image_v1/tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```text
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-multipart
aiosqlite>=0.19.0
torch>=2.0.0
ultralytics>=8.0.0
numpy>=1.24.0
opencv-python>=4.8.0
Pillow>=10.0.0
pydantic>=2.0.0
aiofiles>=23.0.0
pytest>=7.0.0
httpx>=0.24.0
```

- [ ] **Step 2: Create all __init__.py files**

```bash
touch code/algae_image_v1/backend/__init__.py
touch code/algae_image_v1/backend/app/__init__.py
touch code/algae_image_v1/backend/app/routes/__init__.py
touch code/algae_image_v1/backend/app/services/__init__.py
touch code/algae_image_v1/core_engine/__init__.py
touch code/algae_image_v1/tests/__init__.py
```

- [ ] **Step 3: Create empty frontend directories**

```bash
mkdir -p code/algae_image_v1/frontend/css
mkdir -p code/algae_image_v1/frontend/js
```

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/requirements.txt code/algae_image_v1/**/__init__.py
git commit -m "feat(v1): scaffold directory structure and requirements

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 1: Copy Weight Files

**Files:**
- Copy: `weights/rdn_polarization.pth` ← `code/algae_guardian/ml/models/rdn_polarization.pth`
- Copy: `weights/best.pt` ← `results/yolo_results_20260522/yolo_artifacts/weights/best.pt`

- [ ] **Step 1: Copy RDN weight**

```bash
cp code/algae_guardian/ml/models/rdn_polarization.pth code/algae_image_v1/weights/rdn_polarization.pth
```

- [ ] **Step 2: Copy YOLO weight**

```bash
cp results/yolo_results_20260522/yolo_artifacts/weights/best.pt code/algae_image_v1/weights/best.pt
```

- [ ] **Step 3: Verify weights exist and have correct sizes**

```bash
ls -lh code/algae_image_v1/weights/rdn_polarization.pth   # expect ~2.5MB
ls -lh code/algae_image_v1/weights/best.pt                  # expect ~22MB
python -c "import torch; w=torch.load('code/algae_image_v1/weights/rdn_polarization.pth', map_location='cpu'); print('RDN keys:', len(w))"
python -c "from ultralytics import YOLO; m=YOLO('code/algae_image_v1/weights/best.pt'); print('YOLO classes:', m.names)"
```

Expected: RDN checkpoint loads without error. YOLO model reports 95 classes.

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/weights/
git commit -m "feat(v1): add model weights (RDN PSNR 62.46dB + YOLOv8s mAP50 84.7%)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: core_engine/config.py — Algae Species Definitions

**Files:**
- Create: `code/algae_image_v1/core_engine/config.py`
- Source: `code/algae_guardian/ml/config.py`

- [ ] **Step 1: Read existing config for reference patterns**

```bash
cat code/algae_guardian/ml/config.py
```

- [ ] **Step 2: Write config.py with LifeWatch 95 classes**

```python
"""Algae species definitions, risk thresholds, and FOV parameters."""
from typing import Dict, Tuple

# ── LifeWatch 95 Class Mapping ──────────────────────────────────────────
# Model trained on LifeWatch FlowCam dataset (337k particles, 95 classes)
# best.pt @ mAP50=84.7%, trained with structure-tensor polarization

LIFEWATCH_95_CLASSES: Dict[int, str] = {
    0: "Anabaena", 1: "Aphanizomenon", 2: "Aphanocapsa", 3: "Aphanothece",
    4: "Asterionella", 5: "Aulacoseira", 6: "Bitrichia", 7: "Botryococcus",
    8: "Ceratium", 9: "Chlamydomonas", 10: "Chlorella", 11: "Chroococcus",
    12: "Closterium", 13: "Coelastrum", 14: "Cosmarium", 15: "Cryptomonas",
    16: "Cyclotella", 17: "Cylindrospermopsis", 18: "Desmodesmus",
    19: "Dictyosphaerium", 20: "Didymocystis", 21: "Dinobryon",
    22: "Dolichospermum", 23: "Elakatothrix", 24: "Eudorina",
    25: "Euglena", 26: "Fragilaria", 27: "Gloeocapsa", 28: "Gloeotrichia",
    29: "Gomphonema", 30: "Gonyostomum", 31: "Gymnodinium",
    32: "Kirchneriella", 33: "Limnothrix", 34: "Mallomonas",
    35: "Melosira", 36: "Merismopedia", 37: "Micrasterias",
    38: "Microcystis", 39: "Monoraphidium", 40: "Mougeotia",
    41: "Navicula", 42: "Nitzschia", 43: "Nodularia", 44: "Nostoc",
    45: "Oocystis", 46: "Oscillatoria", 47: "Pandorina", 48: "Pediastrum",
    49: "Peridinium", 50: "Phacus", 51: "Phormidium", 52: "Pinnularia",
    53: "Planktolyngbya", 54: "Planktothrix", 55: "Pseudanabaena",
    56: "Radiococcus", 57: "Raphidiopsis", 58: "Rhodomonas",
    59: "Scenedesmus", 60: "Selenastrum", 61: "Snowella",
    62: "Sphaerocystis", 63: "Spirogyra", 64: "Spiroides",
    65: "Staurastrum", 66: "Staurodesmus", 67: "Stephanodiscus",
    68: "Synedra", 69: "Synura", 70: "Tabellaria", 71: "Tetraedron",
    72: "Tetrastrum", 73: "Trachelomonas", 74: "Tribonema",
    75: "Uroglena", 76: "Volvox", 77: "Woronichinia", 78: "Zygnema",
    79: "Non-phytoplankton_1", 80: "Non-phytoplankton_2",
    81: "Non-phytoplankton_3", 82: "Non-phytoplankton_4",
    83: "Non-phytoplankton_5", 84: "Other_phytoplankton_1",
    85: "Other_phytoplankton_2", 86: "Other_phytoplankton_3",
    87: "Other_phytoplankton_4", 88: "Other_phytoplankton_5",
    89: "Other_phytoplankton_6", 90: "Other_phytoplankton_7",
    91: "Other_phytoplankton_8", 92: "Other_phytoplankton_9",
    93: "Other_phytoplankton_10", 94: "Other_phytoplankton_11",
}

# ── Risk Level Mapping ──────────────────────────────────────────────────
# Toxigenic / bloom-forming genera → high risk
# Bloom indicators → medium risk
# Common / non-toxic → low risk

RISK_LEVELS: Dict[str, str] = {
    "Microcystis": "high",
    "Woronichinia": "high",
    "Dolichospermum": "high",
    "Anabaena": "high",
    "Cylindrospermopsis": "high",
    "Raphidiopsis": "high",
    "Nodularia": "high",
    "Planktothrix": "high",
    "Aphanizomenon": "high",
    "Oscillatoria": "high",
    "Gymnodinium": "high",
    "Dinobryon": "medium",
    "Ceratium": "medium",
    "Peridinium": "medium",
    "Aulacoseira": "medium",
    "Fragilaria": "medium",
    "Spiroides": "medium",
}

RISK_COLORS: Dict[str, str] = {
    "high": "#dc2626",
    "medium": "#f59e0b",
    "low": "#16a34a",
}

RISK_LABELS_ZH: Dict[str, str] = {
    "high": "高危",
    "medium": "中危",
    "low": "低危",
}

# ── Confidence Threshold ────────────────────────────────────────────────
DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_IOU: float = 0.7
DEFAULT_IMAGE_SIZE: Tuple[int, int] = (320, 320)

# ── Quality Thresholds ──────────────────────────────────────────────────
Q_GOOD: float = 0.7
Q_FAIR: float = 0.4

# ── I_enh v2 Parameters ─────────────────────────────────────────────────
IENH_ALPHA: float = 0.6
IENH_BETA: float = 0.25
IENH_GAMMA: float = 0.35


def get_class_name(class_id: int) -> str:
    return LIFEWATCH_95_CLASSES.get(class_id, f"Unknown_{class_id}")


def get_risk_level(class_name: str) -> str:
    return RISK_LEVELS.get(class_name, "low")


def get_risk_label(risk_level: str) -> str:
    return RISK_LABELS_ZH.get(risk_level, risk_level)


def get_risk_color(risk_level: str) -> str:
    return RISK_COLORS.get(risk_level, "#6b7280")
```

- [ ] **Step 3: Verify import**

```bash
cd code/algae_image_v1 && python -c "from core_engine.config import LIFEWATCH_95_CLASSES, get_risk_level; print(f'{len(LIFEWATCH_95_CLASSES)} classes'); print(f'Microcystis risk: {get_risk_level(\"Microcystis\")}')"
```

Expected: `95 classes`, `Microcystis risk: high`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/core_engine/config.py
git commit -m "feat(v1): add LifeWatch 95-class config with risk mapping

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: core_engine/polarization_sim.py — Structure Tensor Polarization

**Files:**
- Create: `code/algae_image_v1/core_engine/polarization_sim.py`
- Source: `code/algae_guardian/image_processing/polarization_sim.py`

- [ ] **Step 1: Read source file to understand structure**

```bash
wc -l code/algae_guardian/image_processing/polarization_sim.py
head -60 code/algae_guardian/image_processing/polarization_sim.py
```

- [ ] **Step 2: Write polarization_sim.py — extract only the structure tensor method**

Read the source and note the key function signature. The file at `algae_guardian/image_processing/polarization_sim.py` contains both structure-tensor and HSV methods. Extract only the structure-tensor `simulate_polarization()` function into the new file.

The module must export:
```python
def simulate_polarization(rgb_image: np.ndarray) -> np.ndarray:
    """
    Simulate 4-channel polarization from RGB using structure tensor.
    
    Args:
        rgb_image: (H, W, 3) uint8 RGB image
    
    Returns:
        (4, H, W) float32 array: I0, I45, I90, I135
    """
```

- [ ] **Step 3: Validate the module works**

```bash
cd code/algae_image_v1 && python -c "
import cv2, numpy as np
from core_engine.polarization_sim import simulate_polarization
img = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
result = simulate_polarization(img)
assert result.shape == (4, 128, 128), f'Expected (4,128,128), got {result.shape}'
assert result.dtype == np.float32
print('polarization_sim OK: shape', result.shape)
"
```

Expected: `polarization_sim OK: shape (4, 128, 128)`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/core_engine/polarization_sim.py
git commit -m "feat(v1): migrate structure-tensor polarization simulation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: core_engine/reconstructor.py — RDN Polarization Reconstruction

**Files:**
- Create: `code/algae_image_v1/core_engine/reconstructor.py`
- Source: `code/algae_guardian/ml/reconstructor.py`

- [ ] **Step 1: Read source file**

```bash
cat code/algae_guardian/ml/reconstructor.py
```

- [ ] **Step 2: Write reconstructor.py**

Extract the RDN model class and the `load_rdn_model()` / `reconstruct()` functions. Modify import paths to reference `core_engine.config` and local weights path. Strip cloud-training references.

Key functions:
```python
class RDN(nn.Module):
    """Residual Dense Network: 4ch → 16feat → 12blocks×6layers → 4ch"""
    ...

def load_rdn_model(weights_path: str, device: str = "cpu") -> nn.Module:
    """Load RDN from checkpoint, return model in eval mode."""
    ...

def reconstruct(model: nn.Module, I_channels: np.ndarray, device: str = "cpu") -> np.ndarray:
    """
    Run RDN reconstruction on 4-channel polarization input.
    
    Args:
        model: loaded RDN model
        I_channels: (4, H, W) float32 noisy polarization
        device: 'cpu' or 'cuda'
    
    Returns:
        (4, H, W) float32 denoised polarization
    """
    ...
```

- [ ] **Step 3: Validate reconstruction works end-to-end**

```bash
cd code/algae_image_v1 && python -c "
import numpy as np
from core_engine.reconstructor import load_rdn_model, reconstruct
model = load_rdn_model('weights/rdn_polarization.pth', device='cpu')
I_noisy = np.random.randn(4, 128, 128).astype(np.float32) * 0.1 + 0.5
I_clean = reconstruct(model, I_noisy, device='cpu')
assert I_clean.shape == (4, 128, 128), f'Expected (4,128,128), got {I_clean.shape}'
print('reconstructor OK: PSNR ~', round(float(np.mean((I_clean - 0.5)**2)), 4))
"
```

Expected: `reconstructor OK: PSNR ~ ...`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/core_engine/reconstructor.py
git commit -m "feat(v1): migrate RDN reconstruction module

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: core_engine/enhancement.py — I_enh v2 Enhancement

**Files:**
- Create: `code/algae_image_v1/core_engine/enhancement.py`
- Source: `code/algae_guardian/image_processing/enhancement.py`

- [ ] **Step 1: Read source file**

```bash
cat code/algae_guardian/image_processing/enhancement.py
```

- [ ] **Step 2: Write enhancement.py — I_enh v2 only**

Strip v1 code. Export:

```python
def compute_stokes(I_channels: np.ndarray) -> dict:
    """
    Compute Stokes parameters from 4-channel polarization.
    
    Args:
        I_channels: (4, H, W) array [I0, I45, I90, I135]
    
    Returns:
        dict with keys: S0, S1, S2, DoLP, AoP
    """
    I0, I45, I90, I135 = I_channels[0], I_channels[1], I_channels[2], I_channels[3]
    S0 = I0 + I90
    S1 = I0 - I90
    S2 = I45 - I135
    eps = 1e-8
    DoLP = np.sqrt(S1**2 + S2**2) / (S0 + eps)
    AoP = 0.5 * np.arctan2(S2, S1 + eps)
    return {"S0": S0, "S1": S1, "S2": S2, "DoLP": DoLP, "AoP": AoP}


def enhance(I_channels: np.ndarray,
            alpha: float = 0.6, beta: float = 0.25, gamma: float = 0.35) -> np.ndarray:
    """
    I_enh v2: de-scattering enhancement.
    
    I_enh = Norm(S0 * (1 + alpha - gamma*DoLP + beta*|sin(2*AoP)|*DoLP))
    
    Args:
        I_channels: (4, H, W) float32 cleaned polarization
    
    Returns:
        (H, W) float32 enhanced grayscale image
    """
    ...
```

- [ ] **Step 3: Validate enhancement**

```bash
cd code/algae_image_v1 && python -c "
import numpy as np
from core_engine.enhancement import compute_stokes, enhance
I = np.abs(np.random.randn(4, 128, 128).astype(np.float32)) * 0.5 + 0.5
stokes = compute_stokes(I)
for k in ['S0','S1','S2','DoLP','AoP']:
    assert k in stokes, f'Missing {k}'
I_enh = enhance(I)
assert I_enh.shape == (128, 128), f'Expected (128,128), got {I_enh.shape}'
assert I_enh.min() >= 0 and I_enh.max() <= 1.0, 'Value range error'
print('enhancement OK: range [{:.3f}, {:.3f}]'.format(I_enh.min(), I_enh.max()))
"
```

Expected: `enhancement OK: range [0.xxx, 1.xxx]`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/core_engine/enhancement.py
git commit -m "feat(v1): migrate I_enh v2 de-scattering enhancement

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: core_engine/inference.py — YOLO Detection Wrapper

**Files:**
- Create: `code/algae_image_v1/core_engine/inference.py`
- Source: `code/algae_guardian/ml/inference.py`

- [ ] **Step 1: Read source file**

```bash
cat code/algae_guardian/ml/inference.py
```

- [ ] **Step 2: Write inference.py**

Export:

```python
from ultralytics import YOLO
import numpy as np
from .config import DEFAULT_CONFIDENCE, DEFAULT_IOU, get_class_name, get_risk_level


def load_yolo(weights_path: str, device: str = "cpu") -> YOLO:
    """Load YOLOv8s model."""
    model = YOLO(weights_path)
    model.to(device)
    return model


def detect(model: YOLO,
           I_enh: np.ndarray,
           conf: float = DEFAULT_CONFIDENCE,
           iou: float = DEFAULT_IOU) -> list[dict]:
    """
    Run YOLO detection on enhanced image.
    
    Args:
        model: loaded YOLO model
        I_enh: (H, W) float32 or uint8 enhanced grayscale
        conf: confidence threshold
        iou: NMS IoU threshold
    
    Returns:
        list of dicts: [{class_id, class_name, confidence, bbox:[x1,y1,x2,y2], risk_level}]
    """
    ...
```

- [ ] **Step 3: Validate inference loads and runs**

```bash
cd code/algae_image_v1 && python -c "
import numpy as np
from core_engine.inference import load_yolo, detect
model = load_yolo('weights/best.pt', device='cpu')
img = np.random.randint(0, 255, (320, 320), dtype=np.uint8)
results = detect(model, img, conf=0.5)
print(f'inference OK: {len(results)} detections on random noise')
assert isinstance(results, list)
"
```

Expected: `inference OK: 0 detections on random noise` (correct — random noise has no algae)

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/core_engine/inference.py
git commit -m "feat(v1): migrate YOLOv8s detection wrapper (95 classes)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: core_engine/quality.py — Q Quality Scoring

**Files:**
- Create: `code/algae_image_v1/core_engine/quality.py`
- Source: `code/algae_guardian/image_processing/quality.py`

- [ ] **Step 1: Read and migrate quality.py**

```bash
cat code/algae_guardian/image_processing/quality.py
```

- [ ] **Step 2: Write quality.py**

Export:
```python
def compute_q_score(I_channels: np.ndarray) -> float:
    """
    Compute Q quality score from reconstructed polarization.
    Based on DoLP contrast and SNR.
    
    Args:
        I_channels: (4, H, W) cleaned polarization
    
    Returns:
        float in [0, 1], higher = better quality
    """
    ...


def quality_label(q_score: float) -> str:
    """Map Q score to label: Good / Fair / Poor"""
    if q_score >= 0.7: return "Good"
    if q_score >= 0.4: return "Fair"
    return "Poor"
```

- [ ] **Step 3: Validate**

```bash
cd code/algae_image_v1 && python -c "
import numpy as np
from core_engine.quality import compute_q_score, quality_label
I = np.abs(np.random.randn(4, 128, 128).astype(np.float32)) * 0.3 + 0.5
q = compute_q_score(I)
label = quality_label(q)
print(f'quality OK: Q={q:.3f}, label={label}')
assert 0 <= q <= 1.0
"
```

Expected: `quality OK: Q=0.xxx, label=...`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/core_engine/quality.py
git commit -m "feat(v1): migrate Q quality scoring module

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Backend Foundation — config, database, schemas

**Files:**
- Create: `code/algae_image_v1/backend/app/config.py`
- Create: `code/algae_image_v1/backend/app/database.py`
- Create: `code/algae_image_v1/backend/app/schemas.py`

- [ ] **Step 1: Write config.py**

```python
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
```

- [ ] **Step 2: Write database.py**

```python
"""SQLite database initialization and connection management."""
import aiosqlite
import os
from .config import DB_PATH, DATA_DIR, UPLOAD_DIR, RESULT_DIR


async def init_db():
    """Create tables and data directories."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(RESULT_DIR, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS detection_history (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                image_path TEXT NOT NULL,
                result_path TEXT NOT NULL,
                detections TEXT NOT NULL,
                q_score REAL,
                risk_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS batch_tasks (
                id TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get async database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
```

- [ ] **Step 3: Write schemas.py**

```python
"""Pydantic request/response models."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DetectionItem(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]
    risk_level: str  # high / medium / low


class SingleDetectResponse(BaseModel):
    id: str
    filename: str
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    result_image_url: str
    processing_time_ms: float


class BatchResult(BaseModel):
    filename: str
    detections: list[DetectionItem]
    status: str  # "ok" | "error"
    error: Optional[str] = None


class BatchSummary(BaseModel):
    total_detections: int
    high_risk_count: int
    avg_q_score: float


class BatchDetectResponse(BaseModel):
    batch_id: str
    total: int
    results: list[BatchResult]
    summary: BatchSummary


class StatsResponse(BaseModel):
    total_detections: int
    today_count: int
    class_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    recent_detections: list[dict]


class HistoryItem(BaseModel):
    id: str
    filename: str
    risk_level: Optional[str]
    q_score: Optional[float]
    created_at: str


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    limit: int
```

- [ ] **Step 4: Validate imports**

```bash
cd code/algae_image_v1 && python -c "from backend.app.config import RDN_WEIGHTS, YOLO_WEIGHTS; print('config OK:', RDN_WEIGHTS)"
cd code/algae_image_v1 && python -c "from backend.app.schemas import DetectionItem; print('schemas OK')"
```

Expected: both print without error.

- [ ] **Step 5: Commit**

```bash
git add code/algae_image_v1/backend/app/config.py code/algae_image_v1/backend/app/database.py code/algae_image_v1/backend/app/schemas.py
git commit -m "feat(v1): add backend foundation (config, database, schemas)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Backend Pipeline Service

**Files:**
- Create: `code/algae_image_v1/backend/app/services/pipeline.py`
- Create: `code/algae_image_v1/backend/app/services/__init__.py`

- [ ] **Step 1: Write pipeline.py**

```python
"""Pipeline orchestrator: polarize → RDN reconstruct → I_enh enhance → YOLO detect."""
import time
import uuid
import cv2
import numpy as np
from pathlib import Path

from core_engine.polarization_sim import simulate_polarization
from core_engine.enhancement import enhance
from core_engine.inference import detect
from core_engine.quality import compute_q_score


class PipelineRunner:
    """Holds pre-loaded models and runs the full detection pipeline."""

    def __init__(self, rdn_model, yolo_model, device: str = "cpu"):
        self.rdn = rdn_model
        self.yolo = yolo_model
        self.device = device

    def run(self, image_path: str) -> dict:
        """
        Execute full pipeline on a single image.

        Args:
            image_path: path to RGB micrograph

        Returns:
            dict with keys: detections, q_score, result_image, processing_time_ms
        """
        t0 = time.time()

        # 1. Load RGB image
        rgb = cv2.imread(image_path)
        if rgb is None:
            raise ValueError(f"Cannot read image: {image_path}")
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        # 2. Structure-tensor polarization simulation
        from core_engine.reconstructor import reconstruct
        I_channels = simulate_polarization(rgb)

        # 3. RDN reconstruction
        I_clean = reconstruct(self.rdn, I_channels, device=self.device)

        # 4. I_enh v2 enhancement
        I_enh = enhance(I_clean)

        # 5. YOLO detection
        detections = detect(self.yolo, I_enh)

        # 6. Q quality score
        q_score = compute_q_score(I_clean)

        # 7. Draw detection boxes on original image
        result_img = self._draw_boxes(rgb, detections)

        elapsed_ms = (time.time() - t0) * 1000

        return {
            "detections": detections,
            "q_score": float(q_score),
            "result_image": result_img,
            "processing_time_ms": elapsed_ms,
        }

    def _draw_boxes(self, rgb: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Draw YOLO detection boxes and labels on the RGB image."""
        from core_engine.config import get_risk_color
        img = rgb.copy()
        h, w = img.shape[:2]
        for d in detections:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            color_hex = get_risk_color(d.get("risk_level", "low"))
            # Convert hex to BGR
            r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
            color_bgr = (b, g, r)
            cv2.rectangle(img, (x1, y1), (x2, y2), color_bgr, 2)
            label = f"{d['class_name']} {d['confidence']:.2f}"
            cv2.putText(img, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 1)
        return img
```

- [ ] **Step 2: Verify pipeline import**

```bash
cd code/algae_image_v1 && python -c "from backend.app.services.pipeline import PipelineRunner; print('pipeline OK: PipelineRunner imported')"
```

Expected: `pipeline OK: PipelineRunner imported`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/backend/app/services/
git commit -m "feat(v1): add pipeline orchestrator service

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: Backend Detection Route

**Files:**
- Create: `code/algae_image_v1/backend/app/routes/detection.py`

- [ ] **Step 1: Write detection.py**

```python
"""Detection API routes: single image + batch processing."""
import uuid
import json
import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import aiosqlite
import aiofiles
import cv2

from ..config import UPLOAD_DIR, RESULT_DIR
from ..database import get_db
from ..schemas import (
    SingleDetectResponse, BatchDetectResponse,
    BatchResult, BatchSummary, DetectionItem,
)

router = APIRouter(prefix="/api/v1", tags=["detection"])


def get_pipeline():
    """Dependency: get pipeline runner from app state."""
    from ..main import pipeline_runner
    if pipeline_runner is None:
        raise HTTPException(503, "Models not loaded yet")
    return pipeline_runner


async def _save_upload(file: UploadFile) -> tuple[str, str]:
    """Save uploaded file, return (file_id, file_path)."""
    file_id = uuid.uuid4().hex
    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    filename = f"{file_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())
    return file_id, filepath


async def _save_result(file_id: str, result_img) -> str:
    """Save result image, return relative URL path."""
    result_filename = f"{file_id}.png"
    result_path = os.path.join(RESULT_DIR, result_filename)
    cv2.imwrite(result_path, cv2.cvtColor(result_img, cv2.COLOR_RGB2BGR))
    return f"/static/results/{result_filename}"


def _get_overall_risk(detections: list[dict]) -> Optional[str]:
    """Determine overall risk from all detections."""
    risks = [d.get("risk_level", "low") for d in detections]
    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    if risks:
        return "low"
    return None


@router.post("/detect", response_model=SingleDetectResponse)
async def detect_single(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Upload a single micrograph and run detection pipeline."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    file_id, filepath = await _save_upload(file)

    try:
        result = pipeline.run(filepath)
    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {str(e)}")

    result_url = await _save_result(file_id, result["result_image"])

    detection_items = [
        DetectionItem(
            class_id=d["class_id"],
            class_name=d["class_name"],
            confidence=round(d["confidence"], 4),
            bbox=[round(v, 1) for v in d["bbox"]],
            risk_level=d.get("risk_level", "low"),
        )
        for d in result["detections"]
    ]

    risk = _get_overall_risk(result["detections"])

    # Write to history DB
    await db.execute(
        """INSERT INTO detection_history (id, filename, image_path, result_path, detections, q_score, risk_level)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (file_id, file.filename, filepath, result_url, json.dumps([d.model_dump() for d in detection_items]),
         round(result["q_score"], 4), risk),
    )
    await db.commit()

    return SingleDetectResponse(
        id=file_id,
        filename=file.filename or "unknown",
        detections=detection_items,
        q_score=round(result["q_score"], 4),
        risk_level=risk,
        result_image_url=result_url,
        processing_time_ms=round(result["processing_time_ms"], 1),
    )


@router.post("/detect/batch", response_model=BatchDetectResponse)
async def detect_batch(
    files: list[UploadFile] = File(...),
    pipeline=Depends(get_pipeline),
):
    """Upload multiple images and process as a batch."""
    if len(files) > 50:
        raise HTTPException(400, "Maximum 50 files per batch")

    batch_id = uuid.uuid4().hex
    results = []
    total_detections = 0
    high_risk_count = 0
    q_scores = []

    for f in files:
        try:
            file_id, filepath = await _save_upload(f)
            result = pipeline.run(filepath)
            await _save_result(file_id, result["result_image"])

            dets = result["detections"]
            total_detections += len(dets)
            risks = [d.get("risk_level", "low") for d in dets]
            if "high" in risks:
                high_risk_count += 1
            q_scores.append(result["q_score"])

            results.append(BatchResult(
                filename=f.filename or "unknown",
                detections=[
                    DetectionItem(
                        class_id=d["class_id"], class_name=d["class_name"],
                        confidence=round(d["confidence"], 4),
                        bbox=[round(v, 1) for v in d["bbox"]],
                        risk_level=d.get("risk_level", "low"),
                    ) for d in dets
                ],
                status="ok",
            ))
        except Exception as e:
            results.append(BatchResult(
                filename=f.filename or "unknown",
                detections=[], status="error", error=str(e),
            ))

    avg_q = sum(q_scores) / len(q_scores) if q_scores else 0.0

    return BatchDetectResponse(
        batch_id=batch_id,
        total=len(files),
        results=results,
        summary=BatchSummary(
            total_detections=total_detections,
            high_risk_count=high_risk_count,
            avg_q_score=round(avg_q, 4),
        ),
    )
```

- [ ] **Step 2: Verify route module imports**

```bash
cd code/algae_image_v1 && python -c "from backend.app.routes.detection import router; print('detection route OK')"
```

Expected: `detection route OK`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/backend/app/routes/detection.py
git commit -m "feat(v1): add detection API routes (single + batch)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: Backend Dashboard + History Routes

**Files:**
- Create: `code/algae_image_v1/backend/app/routes/dashboard.py`
- Create: `code/algae_image_v1/backend/app/routes/history.py`

- [ ] **Step 1: Write dashboard.py**

```python
"""Dashboard statistics API."""
import json
from fastapi import APIRouter, Depends
import aiosqlite
from ..database import get_db
from ..schemas import StatsResponse

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/stats", response_model=StatsResponse)
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    """Get aggregate detection statistics."""
    # Total detections
    row = await db.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
    total = row[0]["c"] if row else 0

    # Today's count
    row = await db.execute_fetchall(
        "SELECT COUNT(*) as c FROM detection_history WHERE date(created_at) = date('now')"
    )
    today = row[0]["c"] if row else 0

    # Class distribution (flatten detection JSONs)
    rows = await db.execute_fetchall("SELECT detections FROM detection_history ORDER BY created_at DESC LIMIT 500")
    class_dist: dict[str, int] = {}
    risk_dist: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        try:
            dets = json.loads(r["detections"])
            for d in dets:
                name = d.get("class_name", "Unknown")
                class_dist[name] = class_dist.get(name, 0) + 1
                risk = d.get("risk_level", "low")
                risk_dist[risk] = risk_dist.get(risk, 0) + 1
        except (json.JSONDecodeError, KeyError):
            pass

    # Recent 10
    recent = await db.execute_fetchall(
        "SELECT id, filename, risk_level, q_score, created_at FROM detection_history ORDER BY created_at DESC LIMIT 10"
    )
    recent_list = [
        {"id": r["id"], "filename": r["filename"], "risk_level": r["risk_level"],
         "q_score": r["q_score"], "created_at": str(r["created_at"])}
        for r in recent
    ]

    return StatsResponse(
        total_detections=total,
        today_count=today,
        class_distribution=class_dist,
        risk_distribution=risk_dist,
        recent_detections=recent_list,
    )
```

- [ ] **Step 2: Write history.py**

```python
"""Detection history CRUD API."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite
from ..database import get_db
from ..schemas import HistoryItem, HistoryListResponse

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Paginated detection history."""
    offset = (page - 1) * limit
    rows = await db.execute_fetchall(
        "SELECT id, filename, risk_level, q_score, created_at FROM detection_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    total_row = await db.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
    total = total_row[0]["c"] if total_row else 0

    items = [
        HistoryItem(id=r["id"], filename=r["filename"], risk_level=r["risk_level"],
                    q_score=r["q_score"], created_at=str(r["created_at"]))
        for r in rows
    ]
    return HistoryListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/history/{record_id}")
async def get_history_detail(record_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """Get full detail of a single history record."""
    row = await db.execute_fetchall(
        "SELECT * FROM detection_history WHERE id = ?", (record_id,)
    )
    if not row:
        raise HTTPException(404, "Record not found")
    r = row[0]
    return {
        "id": r["id"], "filename": r["filename"],
        "image_path": r["image_path"], "result_path": r["result_path"],
        "detections": json.loads(r["detections"]),
        "q_score": r["q_score"], "risk_level": r["risk_level"],
        "created_at": str(r["created_at"]),
    }


@router.delete("/history/{record_id}")
async def delete_history(record_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """Delete a history record."""
    cursor = await db.execute("DELETE FROM detection_history WHERE id = ?", (record_id,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "Record not found")
    return {"status": "deleted", "id": record_id}
```

- [ ] **Step 3: Verify imports**

```bash
cd code/algae_image_v1 && python -c "from backend.app.routes.dashboard import router; from backend.app.routes.history import router; print('dashboard + history routes OK')"
```

Expected: `dashboard + history routes OK`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/backend/app/routes/dashboard.py code/algae_image_v1/backend/app/routes/history.py
git commit -m "feat(v1): add dashboard stats + history CRUD API routes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: Backend main.py — FastAPI Application Entry Point

**Files:**
- Create: `code/algae_image_v1/backend/app/main.py`

- [ ] **Step 1: Write main.py**

```python
"""藻影卫士 V1.0 — FastAPI Application Entry Point."""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure core_engine is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.config import HOST, PORT, RDN_WEIGHTS, YOLO_WEIGHTS, UPLOAD_DIR, RESULT_DIR, DATA_DIR
from backend.app.database import init_db

# Global pipeline runner (initialized at startup)
pipeline_runner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, load models. Shutdown: cleanup."""
    global pipeline_runner

    # Init database and directories
    await init_db()
    print(f"[Startup] Database initialized at {DATA_DIR}")

    # Load models
    import torch
    from core_engine.reconstructor import load_rdn_model
    from core_engine.inference import load_yolo
    from backend.app.services.pipeline import PipelineRunner

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Startup] Device: {device}")

    print(f"[Startup] Loading RDN: {RDN_WEIGHTS}")
    rdn = load_rdn_model(RDN_WEIGHTS, device=device)
    print("[Startup] RDN loaded")

    print(f"[Startup] Loading YOLO: {YOLO_WEIGHTS}")
    yolo = load_yolo(YOLO_WEIGHTS, device=device)
    print("[Startup] YOLO loaded")

    pipeline_runner = PipelineRunner(rdn, yolo, device=device)
    print(f"[Startup] Pipeline ready — Algae Guardian V1.0")

    yield

    # Cleanup
    pipeline_runner = None
    print("[Shutdown] Models released")


app = FastAPI(
    title="藻影卫士 V1.0",
    description="偏振显微藻类智能检测系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
from backend.app.routes.detection import router as detect_router
from backend.app.routes.dashboard import router as dashboard_router
from backend.app.routes.history import router as history_router

app.include_router(detect_router)
app.include_router(dashboard_router)
app.include_router(history_router)

# Mount static files
app.mount("/static/results", StaticFiles(directory=RESULT_DIR), name="results")
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
```

- [ ] **Step 2: Verify app can be imported (without starting)**

```bash
cd code/algae_image_v1 && python -c "import sys; sys.path.insert(0,'.'); from backend.app.main import app; print(f'App: {app.title} v{app.version}'); print(f'Routes: {len(app.routes)}')"
```

Expected: `App: 藻影卫士 V1.0 v1.0.0`, `Routes: N`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/backend/app/main.py
git commit -m "feat(v1): add FastAPI main entry point with model preloading

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: Frontend HTML + CSS

**Files:**
- Create: `code/algae_image_v1/frontend/index.html`
- Create: `code/algae_image_v1/frontend/css/style.css`

- [ ] **Step 1: Write style.css**

```css
/* 藻影卫士 V1.0 — Global Styles */
:root {
    --primary: #1e6f5c;
    --primary-light: #29a587;
    --bg: #f8fafb;
    --card: #ffffff;
    --text: #1a1a2e;
    --text-secondary: #6b7280;
    --border: #e5e7eb;
    --risk-high: #dc2626;
    --risk-medium: #f59e0b;
    --risk-low: #16a34a;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
    --radius: 8px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); }
/* ── Header ── */
.header { background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: white; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; }
.header h1 { font-size: 1.25rem; font-weight: 600; }
.header .version { font-size: 0.75rem; opacity: 0.8; }
/* ── Tab Navigation ── */
.tabs { display: flex; gap: 0; background: var(--card); border-bottom: 2px solid var(--border); padding: 0 24px; }
.tab-btn { padding: 12px 24px; border: none; background: none; cursor: pointer; font-size: 0.9rem; color: var(--text-secondary); border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s; }
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }
.tab-btn.placeholder { color: #9ca3af; cursor: not-allowed; }
/* ── Tab Content ── */
.tab-content { display: none; padding: 24px; max-width: 1400px; margin: 0 auto; }
.tab-content.active { display: block; }
/* ── Detection Layout ── */
.detect-layout { display: grid; grid-template-columns: 360px 1fr; gap: 24px; }
.upload-panel { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; }
.upload-zone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 48px 24px; text-align: center; cursor: pointer; transition: all 0.2s; }
.upload-zone:hover { border-color: var(--primary-light); background: #f0fdf9; }
.upload-zone.dragover { border-color: var(--primary); background: #ecfdf7; }
.upload-zone input[type="file"] { display: none; }
.upload-icon { font-size: 2rem; margin-bottom: 8px; }
.result-panel { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; min-height: 400px; }
.result-panel img { max-width: 100%; border-radius: 4px; }
/* ── Detection List ── */
.detect-list { margin-top: 16px; }
.detect-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-radius: 4px; margin-bottom: 4px; }
.detect-item.risk-high { background: #fef2f2; border-left: 3px solid var(--risk-high); }
.detect-item.risk-medium { background: #fffbeb; border-left: 3px solid var(--risk-medium); }
.detect-item.risk-low { background: #f0fdf4; border-left: 3px solid var(--risk-low); }
.risk-badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; }
.risk-badge.high { background: var(--risk-high); }
.risk-badge.medium { background: var(--risk-medium); }
.risk-badge.low { background: var(--risk-low); }
/* ── Stats Cards ── */
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow); padding: 20px; text-align: center; }
.stat-card .number { font-size: 2rem; font-weight: 700; color: var(--primary); }
.stat-card .label { color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; }
/* ── Charts ── */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.chart-card { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; }
.chart-card h3 { margin-bottom: 16px; font-size: 1rem; }
/* ── Table ── */
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
th { background: #f9fafb; font-weight: 600; }
/* ── Buttons ── */
.btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; transition: all 0.15s; }
.btn-primary { background: var(--primary); color: white; }
.btn-primary:hover { background: var(--primary-light); }
.btn-danger { background: var(--risk-high); color: white; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }
/* ── Progress ── */
.progress-bar { width: 100%; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; margin: 12px 0; }
.progress-fill { height: 100%; background: var(--primary); transition: width 0.3s; }
/* ── Empty State ── */
.empty-state { text-align: center; color: var(--text-secondary); padding: 64px 24px; }
.empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
```

- [ ] **Step 2: Write index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>藻影卫士 V1.0</title>
<link rel="stylesheet" href="css/style.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
<!-- Header -->
<div class="header">
  <div>
    <h1>藻影卫士 Algae Guardian</h1>
  </div>
  <span class="version">V1.0</span>
</div>

<!-- Tab Navigation -->
<div class="tabs">
  <button class="tab-btn active" data-tab="detect">检测</button>
  <button class="tab-btn" data-tab="history">历史记录</button>
  <button class="tab-btn" data-tab="dashboard">仪表板</button>
  <button class="tab-btn placeholder" data-tab="devices">设备管理</button>
  <button class="tab-btn placeholder" data-tab="review">人工复核</button>
</div>

<!-- Detection Tab -->
<div class="tab-content active" id="tab-detect">
  <div class="detect-layout">
    <div class="upload-panel">
      <div class="upload-zone" id="upload-zone">
        <div class="upload-icon">📷</div>
        <p>拖拽或点击上传显微图像</p>
        <p style="font-size:0.8rem;color:var(--text-secondary);margin-top:8px;">支持 PNG / JPG / TIF / BMP</p>
        <input type="file" id="file-input" accept="image/*">
      </div>
      <div style="margin-top:12px;display:flex;gap:8px;">
        <button class="btn btn-primary" id="btn-single" disabled>单图检测</button>
        <button class="btn btn-primary" id="btn-batch">批量处理</button>
        <input type="file" id="batch-input" accept="image/*" multiple style="display:none;">
      </div>
      <div id="batch-progress" style="display:none;margin-top:12px;">
        <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>
        <p style="font-size:0.8rem;text-align:center;" id="progress-text"></p>
      </div>
    </div>
    <div class="result-panel" id="result-panel">
      <div class="empty-state">
        <div class="icon">🔬</div>
        <p>上传图像开始藻类检测</p>
      </div>
    </div>
  </div>
</div>

<!-- History Tab -->
<div class="tab-content" id="tab-history">
  <table>
    <thead><tr><th>时间</th><th>文件名</th><th>风险等级</th><th>质量评分</th><th>操作</th></tr></thead>
    <tbody id="history-table-body"><tr><td colspan="5" class="empty-state">加载中...</td></tr></tbody>
  </table>
  <div style="margin-top:16px;display:flex;gap:8px;justify-content:center;" id="history-pagination"></div>
</div>

<!-- Dashboard Tab -->
<div class="tab-content" id="tab-dashboard">
  <div class="stats-grid">
    <div class="stat-card"><div class="number" id="stat-total">0</div><div class="label">总检测次数</div></div>
    <div class="stat-card"><div class="number" id="stat-today">0</div><div class="label">今日检测</div></div>
    <div class="stat-card"><div class="number" id="stat-high">0</div><div class="label" style="color:var(--risk-high);">高危预警</div></div>
  </div>
  <div class="charts-grid">
    <div class="chart-card"><h3>藻类分布</h3><canvas id="chart-class"></canvas></div>
    <div class="chart-card"><h3>风险分布</h3><canvas id="chart-risk"></canvas></div>
  </div>
</div>

<!-- Placeholder Tabs -->
<div class="tab-content" id="tab-devices">
  <div class="empty-state"><div class="icon">⚙️</div><p>设备管理模块将在后续版本开放，敬请期待</p></div>
</div>
<div class="tab-content" id="tab-review">
  <div class="empty-state"><div class="icon">📝</div><p>人工复核模块将在后续版本开放，敬请期待</p></div>
</div>

<script src="js/app.js"></script>
<script src="js/detection.js"></script>
<script src="js/dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 3: Verify HTML structure (check no broken paths)**

```bash
ls code/algae_image_v1/frontend/css/style.css
ls code/algae_image_v1/frontend/js/app.js
```

First CSS will exist. JS files not yet created — expected.

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/frontend/index.html code/algae_image_v1/frontend/css/style.css
git commit -m "feat(v1): add frontend HTML layout + CSS design system

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: Frontend JS — app.js + detection.js

**Files:**
- Create: `code/algae_image_v1/frontend/js/app.js`
- Create: `code/algae_image_v1/frontend/js/detection.js`

- [ ] **Step 1: Write app.js**

```javascript
// 藻影卫士 V1.0 — App Shell
const API = '/api/v1';

document.addEventListener('DOMContentLoaded', () => {
  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      if (btn.classList.contains('placeholder')) return; // ignore placeholder tabs

      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('tab-' + tab);
      if (panel) panel.classList.add('active');

      // Load data when switching tabs
      if (tab === 'dashboard') loadDashboard();
      if (tab === 'history') loadHistory();
    });
  });
});

// Utility
function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleString('zh-CN');
}
```

- [ ] **Step 2: Write detection.js**

```javascript
// 藻影卫士 V1.0 — Detection Module
let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');
  const batchInput = document.getElementById('batch-input');
  const btnSingle = document.getElementById('btn-single');
  const btnBatch = document.getElementById('btn-batch');

  // Click to select file
  zone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      selectedFile = e.target.files[0];
      btnSingle.disabled = false;
      showPreview(selectedFile);
    }
  });

  // Drag and drop
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      selectedFile = e.dataTransfer.files[0];
      btnSingle.disabled = false;
      showPreview(selectedFile);
    }
  });

  // Single detect
  btnSingle.addEventListener('click', runSingleDetection);

  // Batch detect
  btnBatch.addEventListener('click', () => batchInput.click());
  batchInput.addEventListener('change', runBatchDetection);
});

function showPreview(file) {
  const panel = document.getElementById('result-panel');
  const reader = new FileReader();
  reader.onload = (e) => {
    panel.innerHTML = `
      <p style="margin-bottom:12px;color:var(--text-secondary);">预览: <strong>${file.name}</strong> (${(file.size/1024).toFixed(1)} KB)</p>
      <img src="${e.target.result}" style="max-width:100%;max-height:400px;border-radius:4px;" alt="preview">
    `;
  };
  reader.readAsDataURL(file);
}

async function runSingleDetection() {
  if (!selectedFile) return;
  const panel = document.getElementById('result-panel');
  panel.innerHTML = '<div class="empty-state"><p>检测中...</p></div>';

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const resp = await fetch(API + '/detect', { method: 'POST', body: formData });
    if (!resp.ok) { panel.innerHTML = `<div class="empty-state"><p>错误: ${resp.status}</p></div>`; return; }
    const data = await resp.json();
    renderResult(panel, data);
  } catch (err) {
    panel.innerHTML = `<div class="empty-state"><p>连接失败: ${err.message}</p></div>`;
  }
}

function renderResult(panel, data) {
  const riskLabel = {high:'高危', medium:'中危', low:'低危'};
  const risk = data.risk_level || 'low';
  let detList = data.detections.map(d => `
    <div class="detect-item risk-${d.risk_level}">
      <span><strong>${d.class_name}</strong> — 置信度 ${(d.confidence*100).toFixed(1)}%</span>
      <span class="risk-badge ${d.risk_level}">${riskLabel[d.risk_level]||d.risk_level}</span>
    </div>
  `).join('');

  if (detList === '') detList = '<p style="color:var(--text-secondary);">未检测到藻类目标</p>';

  panel.innerHTML = `
    <p style="margin-bottom:8px;"><strong>${data.filename}</strong> — 耗时 ${data.processing_time_ms.toFixed(0)}ms</p>
    <img src="${data.result_image_url}" style="max-width:100%;border-radius:4px;" alt="result">
    <div class="detect-list">${detList}</div>
    <div style="margin-top:12px;display:flex;gap:12px;align-items:center;">
      <span class="risk-badge ${risk}">整体风险: ${riskLabel[risk]}</span>
      <span style="color:var(--text-secondary);">质量评分: ${data.q_score.toFixed(2)}</span>
    </div>
  `;
}

async function runBatchDetection(e) {
  const files = e.target.files;
  if (files.length === 0) return;

  const panel = document.getElementById('result-panel');
  const progDiv = document.getElementById('batch-progress');
  const progFill = document.getElementById('progress-fill');
  const progText = document.getElementById('progress-text');

  progDiv.style.display = 'block';
  const formData = new FormData();
  for (const f of files) formData.append('files', f);

  try {
    progText.textContent = `正在处理 ${files.length} 张图像...`;
    progFill.style.width = '30%';

    const resp = await fetch(API + '/detect/batch', { method: 'POST', body: formData });
    progFill.style.width = '90%';

    if (!resp.ok) { panel.innerHTML = `<div class="empty-state"><p>错误: ${resp.status}</p></div>`; return; }

    const data = await resp.json();
    progFill.style.width = '100%';
    progText.textContent = `完成! 共检测 ${data.summary.total_detections} 个目标, ${data.summary.high_risk_count} 个高危`;

    // Render batch results
    let html = `<h3 style="margin-bottom:16px;">批量检测结果 (${data.total} 张)</h3>`;
    html += '<table><thead><tr><th>文件名</th><th>检测数</th><th>状态</th></tr></thead><tbody>';
    for (const r of data.results) {
      html += `<tr>
        <td>${r.filename}</td>
        <td>${r.status === 'ok' ? r.detections.length : '-'}</td>
        <td>${r.status === 'ok' ? '✅' : '❌ ' + (r.error||'')}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    panel.innerHTML = html;
  } catch (err) {
    panel.innerHTML = `<div class="empty-state"><p>连接失败: ${err.message}</p></div>`;
  } finally {
    setTimeout(() => { progDiv.style.display = 'none'; }, 3000);
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v1/frontend/js/app.js code/algae_image_v1/frontend/js/detection.js
git commit -m "feat(v1): add frontend JS — app shell + detection module

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 15: Frontend JS — dashboard.js (Charts + History Table)

**Files:**
- Create: `code/algae_image_v1/frontend/js/dashboard.js`

- [ ] **Step 1: Write dashboard.js**

```javascript
// 藻影卫士 V1.0 — Dashboard + History Module
let chartClass = null;
let chartRisk = null;

async function loadDashboard() {
  try {
    const resp = await fetch(API + '/dashboard/stats');
    if (!resp.ok) return;
    const data = await resp.json();

    document.getElementById('stat-total').textContent = data.total_detections;
    document.getElementById('stat-today').textContent = data.today_count;
    document.getElementById('stat-high').textContent = (data.risk_distribution || {}).high || 0;

    // Class distribution pie chart
    const classes = Object.keys(data.class_distribution || {});
    const counts = Object.values(data.class_distribution || {});

    if (chartClass) chartClass.destroy();
    const ctx1 = document.getElementById('chart-class');
    if (ctx1 && classes.length > 0) {
      chartClass = new Chart(ctx1, {
        type: 'pie',
        data: {
          labels: classes,
          datasets: [{ data: counts, backgroundColor: generateColors(classes.length) }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { font: { size: 10 } } } } }
      });
    }

    // Risk distribution bar chart
    const rd = data.risk_distribution || {};
    if (chartRisk) chartRisk.destroy();
    const ctx2 = document.getElementById('chart-risk');
    if (ctx2) {
      chartRisk = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: ['高危', '中危', '低危'],
          datasets: [{
            label: '检测数量',
            data: [rd.high || 0, rd.medium || 0, rd.low || 0],
            backgroundColor: ['#dc2626', '#f59e0b', '#16a34a']
          }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
      });
    }
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

function generateColors(n) {
  const base = ['#1e6f5c','#29a587','#f59e0b','#dc2626','#3b82f6','#8b5cf6','#ec4899','#14b8a6',
                '#f97316','#06b6d4','#84cc16','#e11d48','#6366f1','#0ea5e9','#d946ef'];
  while (base.length < n) base.push(`hsl(${Math.random()*360},60%,50%)`);
  return base.slice(0, n);
}

// ── History Table ──
let historyPage = 1;

async function loadHistory(page = 1) {
  historyPage = page;
  try {
    const resp = await fetch(`${API}/history?page=${page}&limit=20`);
    if (!resp.ok) return;
    const data = await resp.json();

    const riskLabel = { high: '高危', medium: '中危', low: '低危' };
    const tbody = document.getElementById('history-table-body');
    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无检测记录</td></tr>';
    } else {
      tbody.innerHTML = data.items.map(item => `
        <tr>
          <td>${formatTime(item.created_at)}</td>
          <td>${item.filename}</td>
          <td><span class="risk-badge ${item.risk_level || 'low'}">${riskLabel[item.risk_level] || '-'}</span></td>
          <td>${item.q_score ? item.q_score.toFixed(2) : '-'}</td>
          <td>
            <button class="btn btn-sm btn-primary" onclick="viewHistoryDetail('${item.id}')">查看</button>
            <button class="btn btn-sm btn-danger" onclick="deleteHistory('${item.id}')">删除</button>
          </td>
        </tr>
      `).join('');
    }

    // Pagination
    const totalPages = Math.ceil(data.total / 20);
    const pagDiv = document.getElementById('history-pagination');
    pagDiv.innerHTML = '';
    for (let i = 1; i <= totalPages && i <= 20; i++) {
      const btn = document.createElement('button');
      btn.className = 'btn btn-sm ' + (i === page ? 'btn-primary' : '');
      btn.style.cssText = i === page ? '' : 'background:#e5e7eb;';
      btn.textContent = i;
      btn.addEventListener('click', () => loadHistory(i));
      pagDiv.appendChild(btn);
    }
  } catch (err) {
    console.error('History load error:', err);
  }
}

async function viewHistoryDetail(id) {
  try {
    const resp = await fetch(`${API}/history/${id}`);
    if (!resp.ok) return;
    const data = await resp.json();
    // Show detail in a simple modal-like panel
    const panel = document.getElementById('result-panel');
    const riskLabel = { high: '高危', medium: '中危', low: '低危' };
    let detList = (data.detections || []).map(d => `
      <div class="detect-item risk-${d.risk_level}">
        <span><strong>${d.class_name}</strong> — ${(d.confidence*100).toFixed(1)}%</span>
        <span class="risk-badge ${d.risk_level}">${riskLabel[d.risk_level]||d.risk_level}</span>
      </div>
    `).join('');
    panel.innerHTML = `
      <h3 style="margin-bottom:12px;">检测详情: ${data.filename}</h3>
      <img src="${data.result_path}" style="max-width:100%;border-radius:4px;" alt="result">
      <div class="detect-list" style="margin-top:12px;">${detList || '无检测结果'}</div>
      <p style="margin-top:12px;color:var(--text-secondary);">时间: ${formatTime(data.created_at)} | 质量评分: ${data.q_score?.toFixed(2) || '-'}</p>
    `;
    // Switch to detect tab to show the result
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector('[data-tab="detect"]').classList.add('active');
    document.getElementById('tab-detect').classList.add('active');
  } catch (err) {
    console.error('View detail error:', err);
  }
}

async function deleteHistory(id) {
  if (!confirm('确定删除这条记录?')) return;
  try {
    await fetch(`${API}/history/${id}`, { method: 'DELETE' });
    loadHistory(historyPage);
  } catch (err) {
    console.error('Delete error:', err);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v1/frontend/js/dashboard.js
git commit -m "feat(v1): add frontend JS — dashboard charts + history table

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 16: run.bat — One-Click Startup Script

**Files:**
- Create: `code/algae_image_v1/run.bat`

- [ ] **Step 1: Write run.bat**

```batch
@echo off
chcp 65001 >nul
title 藻影卫士 V1.0

echo ============================================
echo   藻影卫士 - Algae Guardian V1.0
echo   偏振显微藻类智能检测系统
echo ============================================
echo.

:: Check weights exist
IF NOT EXIST "weights\rdn_polarization.pth" (
    echo [错误] 未找到 RDN 权重: weights\rdn_polarization.pth
    pause
    exit /b 1
)
IF NOT EXIST "weights\best.pt" (
    echo [错误] 未找到 YOLO 权重: weights\best.pt
    pause
    exit /b 1
)

echo [1/3] 激活 Conda 环境 ican...
call conda activate ican
IF ERRORLEVEL 1 (
    echo [错误] 无法激活 conda 环境 ican，请先创建环境
    pause
    exit /b 1
)

echo [2/3] 检查依赖...
python -c "import fastapi, uvicorn, torch, ultralytics, cv2" 2>nul
IF ERRORLEVEL 1 (
    echo [警告] 部分依赖缺失，正在安装...
    pip install -r requirements.txt
)

echo [3/3] 启动藻影卫士 V1.0...
echo.
echo   后端服务: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   前端界面: http://localhost:8000/app/
echo.
echo   按 Ctrl+C 停止服务
echo ============================================

start "" http://localhost:8000/app/
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

pause
```

- [ ] **Step 2: Commit**

```bash
git add code/algae_image_v1/run.bat
git commit -m "feat(v1): add one-click startup script (run.bat)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 17: Integration Tests

**Files:**
- Create: `code/algae_image_v1/tests/conftest.py`
- Create: `code/algae_image_v1/tests/test_pipeline.py`

- [ ] **Step 1: Write conftest.py**

```python
"""Shared test fixtures."""
import sys
import os
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def rdn_model():
    from core_engine.reconstructor import load_rdn_model
    weights = os.path.join(os.path.dirname(__file__), "..", "weights", "rdn_polarization.pth")
    return load_rdn_model(weights, device="cpu")


@pytest.fixture(scope="session")
def yolo_model():
    from core_engine.inference import load_yolo
    weights = os.path.join(os.path.dirname(__file__), "..", "weights", "best.pt")
    return load_yolo(weights, device="cpu")
```

- [ ] **Step 2: Write test_pipeline.py**

```python
"""Integration tests for the full detection pipeline."""
import sys
import os
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPolarizationSim:
    def test_output_shape(self):
        from core_engine.polarization_sim import simulate_polarization
        img = np.random.randint(0, 255, (128, 256, 3), dtype=np.uint8)
        result = simulate_polarization(img)
        assert result.shape == (4, 128, 256)
        assert result.dtype == np.float32

    def test_value_range(self):
        from core_engine.polarization_sim import simulate_polarization
        img = np.ones((64, 64, 3), dtype=np.uint8) * 128
        result = simulate_polarization(img)
        assert result.min() >= 0.0


class TestEnhancement:
    def test_stokes_output(self):
        from core_engine.enhancement import compute_stokes
        I = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.5 + 0.5
        s = compute_stokes(I)
        for k in ['S0', 'S1', 'S2', 'DoLP', 'AoP']:
            assert k in s

    def test_enhance_shape(self):
        from core_engine.enhancement import enhance
        I = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.5 + 0.5
        result = enhance(I)
        assert result.shape == (64, 64)
        assert result.min() >= 0 and result.max() <= 1.0


class TestInference:
    def test_load_model(self, yolo_model):
        from ultralytics import YOLO
        assert isinstance(yolo_model, YOLO)

    def test_detect_random(self, yolo_model):
        from core_engine.inference import detect
        img = np.random.randint(0, 255, (320, 320), dtype=np.uint8)
        results = detect(yolo_model, img, conf=0.9)
        assert isinstance(results, list)


class TestQuality:
    def test_score_range(self):
        from core_engine.quality import compute_q_score
        I = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.3 + 0.5
        q = compute_q_score(I)
        assert 0.0 <= q <= 1.0


class TestConfig:
    def test_class_count(self):
        from core_engine.config import LIFEWATCH_95_CLASSES
        assert len(LIFEWATCH_95_CLASSES) == 95

    def test_risk_mapping(self):
        from core_engine.config import get_risk_level
        assert get_risk_level("Microcystis") == "high"
        assert get_risk_level("Unknown_X") == "low"
```

- [ ] **Step 3: Run tests**

```bash
cd code/algae_image_v1 && python -m pytest tests/test_pipeline.py -v --tb=short
```

Expected: all tests pass (may take ~30s for model loading).

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v1/tests/
git commit -m "feat(v1): add integration tests for pipeline + core engine

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 18: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Start the server**

```bash
cd code/algae_image_v1 && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
sleep 10
```

- [ ] **Step 2: Test API health via curl**

```bash
curl -s http://localhost:8000/docs | head -20
curl -s http://localhost:8000/api/v1/dashboard/stats | python -m json.tool
```

Expected: `/docs` returns HTML, `/dashboard/stats` returns JSON with `total_detections: 0`.

- [ ] **Step 3: Test single detection with a real image**

Find any .tif or .jpg in the project to use as a test image:
```bash
# Use a sample FMPD image if available
TEST_IMG=$(ls data/fmpd_download/extracted/dataset/dataset/*.tif 2>/dev/null | head -1)
if [ -z "$TEST_IMG" ]; then
    # Generate a synthetic test image
    python -c "import cv2; import numpy as np; cv2.imwrite('/tmp/test_algae.png', np.random.randint(0,255,(640,480,3),dtype=np.uint8))"
    TEST_IMG="/tmp/test_algae.png"
fi
curl -s -X POST http://localhost:8000/api/v1/detect -F "file=@${TEST_IMG}" | python -m json.tool
```

Expected: JSON response with `id`, `filename`, `detections` (list), `q_score`, `result_image_url`.

- [ ] **Step 4: Test frontend is accessible**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/app/
```

Expected: `200`

- [ ] **Step 5: Kill test server**

```bash
kill %1 2>/dev/null || true
```

- [ ] **Step 6: Final commit if needed**

```bash
git status
# commit any remaining changes
```

---

## Plan Summary

| Phase | Tasks | Files Created |
|-------|-------|---------------|
| Foundation | 0-1 | 9 (dirs, requirements, weights) |
| core_engine | 2-7 | 6 (.py modules) |
| Backend | 8-12 | 8 (.py modules) |
| Frontend | 13-15 | 5 (html, css, 3× js) |
| Startup | 16 | 1 (run.bat) |
| Tests | 17 | 2 (conftest, test_pipeline) |
| Verify | 18 | 0 (manual verification) |

**Total: 19 tasks, ~35 files**

---

**Plan complete. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast parallel iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
