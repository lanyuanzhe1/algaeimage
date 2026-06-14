# Structure Tensor + RDN Pipeline Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace HSV polarization with Structure Tensor + RDN in V2 demo, raising FMPD mAP50 from 35.4% to 73.9%.

**Architecture:** Swap `polarization_sim.py` from HSV to structure tensor (V1 code), drop RDN into `PipelineRunner._run_core()`, load RDN at startup. Existing `reconstructor.py` and `enhancement.py` are already complete — just need to be wired in.

**Tech Stack:** Python 3.11, PyTorch, numpy, cv2, FastAPI. Conda env `ican`.

---

### Task 1: Replace polarization_sim.py — HSV → Structure Tensor

**Files:**
- Replace: `code/algae_image_v2/core_engine/polarization_sim.py`

The current file is the HSV implementation. Replace it entirely with V1's structure tensor version (`code/algae_image_v1/core_engine/polarization_sim.py`). Both have the same function signature: `simulate_polarization(rgb) → (4, H, W) float32`, so downstream code needs zero changes.

- [ ] **Step 1: Copy structure tensor implementation from V1**

Copy the entire content of `code/algae_image_v1/core_engine/polarization_sim.py` to `code/algae_image_v2/core_engine/polarization_sim.py`. The file is at:

```
e:\code\codex\code\algae_image_v1\core_engine\polarization_sim.py
```

The key function is `simulate_polarization(rgb_image, polarization_strength=1.0, sigma=2.0)` which computes structure tensor, derives orientation/anisotropy, and applies Malus law to produce 4-channel output. Keep existing `hsv_polarization.py` untouched as fallback.

- [ ] **Step 2: Verify import still works**

```bash
cd e:/code/codex/code/algae_image_v2
python -c "from core_engine.polarization_sim import simulate_polarization; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/core_engine/polarization_sim.py
git commit -m "feat: replace HSV polarization with structure tensor (V1 port)"
```

---

### Task 2: Update core_engine/config.py — enable RDN, switch to v8s

**Files:**
- Modify: `code/algae_image_v2/core_engine/config.py:61-76`

Three changes:
1. `SKIP_RDN = False` (was `True`)
2. `DEFAULT_MODEL = "v8s"` (was `"v8l"`)
3. Restore I_enh parameters to V1 defaults (α=0.6, β=0.25, γ=0.35) — must match what YOLOv8s was trained on

- [ ] **Step 1: Edit config.py**

In `code/algae_image_v2/core_engine/config.py`, make these exact changes:

```python
# Line 61: was SKIP_RDN: bool = True
SKIP_RDN: bool = False   # Structure tensor needs RDN denoising

# Line 58: was DEFAULT_MODEL: str = "v8l"
DEFAULT_MODEL: str = "v8s"

# Lines 73-75: was IENH_ALPHA=0.05, IENH_GAMMA=0.30
IENH_ALPHA: float = 0.6    # V1 default (matched to YOLOv8s training)
IENH_BETA: float = 0.25    # unchanged
IENH_GAMMA: float = 0.35   # V1 default
```

- [ ] **Step 2: Verify config loads**

```bash
cd e:/code/codex/code/algae_image_v2
python -c "from core_engine.config import SKIP_RDN, DEFAULT_MODEL, IENH_ALPHA; print(f'SKIP_RDN={SKIP_RDN} MODEL={DEFAULT_MODEL} ALPHA={IENH_ALPHA}')"
```

Expected: `SKIP_RDN=False MODEL=v8s ALPHA=0.6`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/core_engine/config.py
git commit -m "feat: enable RDN, switch default model to v8s, restore V1 I_enh params"
```

---

### Task 3: Add RDN to PipelineRunner

**Files:**
- Modify: `code/algae_image_v2/backend/app/services/pipeline.py`

`PipelineRunner.__init__` gains an optional `rdn_model` parameter. `_run_core()` inserts RDN reconstruction between polarization (step 1) and enhancement (step 3). When `rdn_model` is None, falls back to pass-through (current behavior, usable for HSV or CPU-only).

- [ ] **Step 1: Add imports**

At the top of `pipeline.py`, after existing core_engine imports, add:

```python
from core_engine.reconstructor import reconstruct
```

- [ ] **Step 2: Add rdn_model to PipelineRunner.__init__**

Replace the `__init__` method (lines 17-20):

```python
def __init__(self, yolo_model, device: str = "cpu", model_key: str = DEFAULT_MODEL,
             rdn_model=None):
    self.yolo = yolo_model
    self.device = device
    self.model_key = model_key
    self.rdn_model = rdn_model
```

- [ ] **Step 3: Update create() factory**

Replace the `create` classmethod (lines 22-26):

```python
@classmethod
def create(cls, model_key: str = DEFAULT_MODEL, device: str = "cpu",
           rdn_model=None):
    """Factory: load YOLO by model key from AVAILABLE_MODELS config."""
    yolo = load_yolo_by_key(model_key, device)
    return cls(yolo, device, model_key, rdn_model)
```

- [ ] **Step 4: Insert RDN step in _run_core**

Replace lines 54-55 (the RDN skip comment and pass-through):

```python
# 2. RDN reconstruction (structure tensor denoising)
if self.rdn_model is not None:
    I_clean = reconstruct(self.rdn_model, I_channels, self.device)
else:
    I_clean = I_channels  # fallback: HSV or CPU-only
```

Keep all other lines unchanged.

- [ ] **Step 5: Verify PipelineRunner imports**

```bash
cd e:/code/codex/code/algae_image_v2
python -c "from backend.app.services.pipeline import PipelineRunner; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add code/algae_image_v2/backend/app/services/pipeline.py
git commit -m "feat: add RDN reconstruction step to PipelineRunner"
```

---

### Task 4: Load RDN at startup in main.py

**Files:**
- Modify: `code/algae_image_v2/backend/app/main.py`

Lifespan loads RDN model after YOLO and passes it to PipelineRunner. Also add RDN weights path to `backend/app/config.py`.

- [ ] **Step 1: Add RDN weights path to backend/app/config.py**

After line 31 (`YOLO_WEIGHTS_V8S = ...`), add:

```python
RDN_WEIGHTS = resource_path("weights/rdn_polarization.pth")
```

- [ ] **Step 2: Load RDN in main.py lifespan**

In `main.py`, replace lines 34-37 (the PipelineRunner.create call) with:

```python
# V2: Structure Tensor pipeline — load RDN + YOLO
from backend.app.services.pipeline import PipelineRunner
from core_engine.reconstructor import load_rdn_model
from backend.app.config import RDN_WEIGHTS

rdn_model = None
if os.path.exists(RDN_WEIGHTS):
    rdn_model = load_rdn_model(RDN_WEIGHTS, device)
    print(f"[Startup] RDN loaded from {RDN_WEIGHTS}")
else:
    print(f"[Startup] RDN weights not found at {RDN_WEIGHTS} — running without RDN")

pipeline_runner = PipelineRunner.create(device=device, rdn_model=rdn_model)
print(f"[Startup] Pipeline ready — Algae Image V2 (StructTensor+RDN, FMPD 5-class)")
```

- [ ] **Step 3: Verify startup logic**

```bash
cd e:/code/codex/code/algae_image_v2
python -c "
from backend.app.config import RDN_WEIGHTS
import os
print('RDN path:', RDN_WEIGHTS)
print('Exists:', os.path.exists(RDN_WEIGHTS))
"
```

Expected: `RDN path: ...weights/rdn_polarization.pth` and `Exists: True`

- [ ] **Step 4: Commit**

```bash
git add code/algae_image_v2/backend/app/config.py code/algae_image_v2/backend/app/main.py
git commit -m "feat: load RDN model at startup, inject into PipelineRunner"
```

---

### Task 5: Update run_with_visualization for RDN

**Files:**
- Modify: `code/algae_image_v2/backend/app/services/pipeline.py`

The visualization pipeline (`run_with_visualization`) currently shows 5 steps. Add an RDN reconstruction step showing the denoised I0 channel after RDN processing.

- [ ] **Step 1: Add RDN visualization step**

In `run_with_visualization()`, after the polarization step (after line 133, the `pol_montage` creation) and before the Stokes step, insert:

```python
# Step 2.5: RDN reconstruction (only when RDN is loaded)
if self.rdn_model is not None:
    rdn_out = reconstruct(self.rdn_model, I_channels, self.device)
    # Show denoised I0 vs original I0 side-by-side
    I0_before = np.clip(I_channels[0] * 255, 0, 255).astype(np.uint8)
    I0_after = np.clip(rdn_out[0] * 255, 0, 255).astype(np.uint8)
    rdn_comparison = np.hstack([
        cv2.cvtColor(I0_before, cv2.COLOR_GRAY2RGB),
        cv2.cvtColor(I0_after, cv2.COLOR_GRAY2RGB),
    ])
    cv2.putText(rdn_comparison, "I0 before RDN", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    cv2.putText(rdn_comparison, "I0 after RDN", (w + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    I_channels = rdn_out  # use denoised channels for subsequent steps
else:
    rdn_comparison = None  # skip this visualization step
```

Then in the `steps` list (after step 2 "偏振模拟"), add:

```python
*([{
    "title": "2.5 RDN偏振重建",
    "image": _rgb_to_b64(rdn_comparison),
    "description": "左: 结构张量I0 (含噪) | 右: RDN去噪I0 (PSNR 62.46dB)",
}] if rdn_comparison is not None else []),
```

- [ ] **Step 2: Verify visualization pipeline**

```bash
cd e:/code/codex/code/algae_image_v2
python -c "
from backend.app.services.pipeline import PipelineRunner
print('PipelineRunner.run_with_visualization ready')
"
```

Expected: `PipelineRunner.run_with_visualization ready`

- [ ] **Step 3: Commit**

```bash
git add code/algae_image_v2/backend/app/services/pipeline.py
git commit -m "feat: add RDN reconstruction visualization step"
```

---

### Task 6: Integration smoke test

**Files:**
- None (test only)

- [ ] **Step 1: Full startup test**

```bash
cd e:/code/codex/code/algae_image_v2
"A:/Anaconda_envs/envs/ican/python.exe" -c "
import os, sys
sys.path.insert(0, '.')
os.chdir('e:/code/codex/code/algae_image_v2')

# Simulate startup
from backend.app.config import RDN_WEIGHTS, resource_path
import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Device: {device}')

from core_engine.reconstructor import load_rdn_model
rdn = load_rdn_model(RDN_WEIGHTS, device)
print('RDN loaded OK')

from core_engine.polarization_sim import simulate_polarization
from core_engine.reconstructor import reconstruct
from core_engine.enhancement import enhance
import numpy as np

# Test on synthetic 256x256 image
rgb = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
channels = simulate_polarization(rgb)
print(f'Polarization: {channels.shape}')

denoised = reconstruct(rdn, channels, device)
print(f'RDN output: {denoised.shape}')

enhanced = enhance(denoised)
print(f'Enhanced: {enhanced.shape}')
print('All pipeline stages OK')
"
```

Expected: all stages pass without errors.

- [ ] **Step 2: Start server and test single detect**

```bash
cd e:/code/codex/code/algae_image_v2
# Start server in background
"A:/Anaconda_envs/envs/ican/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
# Wait for startup
sleep 20
# Test detect endpoint
curl -s http://localhost:8000/docs | head -5
```

Expected: 200 response, Swagger docs load.

- [ ] **Step 3: Cleanup**

Stop uvicorn process if running.

---

### Task 7: Rebuild frontend dist

**Files:**
- Rebuild: `code/algae_image_v2/frontend/dist/`

No frontend code changes needed, but rebuild dist to pick up any stale cache from the v=8 parameter.

- [ ] **Step 1: Build frontend**

```bash
cd e:/code/codex/code/algae_image_v2/frontend
export PATH="A:/Program Files/nodejs:$PATH"
npm run build
```

- [ ] **Step 2: Force-add dist**

```bash
cd e:/code/codex/code/algae_image_v2
git add -f frontend/dist/
git commit -m "build: refresh frontend dist for struct+RDN pipeline"
```
