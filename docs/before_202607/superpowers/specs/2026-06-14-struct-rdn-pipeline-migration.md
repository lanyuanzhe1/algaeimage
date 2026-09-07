# Spec: Structure Tensor + RDN Pipeline Migration for V2 Demo

**Date**: 2026-06-14
**Branch**: HSV
**Goal**: Replace HSV polarization with Structure Tensor + RDN in V2 demo to raise FMPD detection mAP50 from 35.4% to 73.9%.

## Motivation

Current V2 demo pipeline (`RGB → HSV → skip RDN → I_enh v2 → YOLOv8l`) achieves only 35.4% mAP50 on FMPD. The experimental evidence (RDN_HSV_0526) shows:

- Structure Tensor + RDN is a **strong binding**: structure tensor injects physically meaningful polarization noise, RDN removes it
- HSV + RDN is **counterproductive** (33.0% < 35.4%) — HSV has no noise for RDN to remove
- The best FMPD result: Structure Tensor + RDN + I_enh v1 + YOLOv8s → 73.9% mAP50 (train=val, but best available)

## Target Pipeline

```
RGB → Structure Tensor polarization → RDN (62.46dB PSNR) → I_enh v2(α=0.6) → YOLOv8s
```

Every inference parameter must match what the YOLOv8s was trained on:
- Polarization: Structure tensor (sigma=2.0, polarization_strength=1.0)
- RDN: 4→16→16→4, 12 blocks × 6 layers, weights from V1
- Enhancement: I_enh v2 with α=0.6, β=0.25, γ=0.35 (V1 defaults)
- YOLO: YOLOv8s FMPD 5-class, weights at `algae_guardian/data/yolo_results/training/weights/best.pt`

## Files Changed

### 1. `core_engine/polarization_sim.py` — REPLACE

Replace HSV implementation with Structure Tensor from V1 (`code/algae_image_v1/core_engine/polarization_sim.py`).
Same API: `simulate_polarization(rgb) → (4, H, W) float32`.

### 2. `core_engine/config.py` — MODIFY

```python
SKIP_RDN: bool = False          # was True
DEFAULT_MODEL: str = "v8s"      # was "v8l"
IENH_ALPHA: float = 0.6         # was 0.05 (HSV-tuned)
IENH_BETA: float = 0.25         # unchanged
IENH_GAMMA: float = 0.35        # was 0.30
```

Add RDN weights path to AVAILABLE_MODELS metadata.

### 3. `backend/app/services/pipeline.py` — MODIFY

`PipelineRunner` gains an optional `rdn_model` field. When present, `_run_core()` inserts RDN reconstruction between polarization and enhancement:

```python
# Step 1 → 2: RDN reconstruction (when model loaded)
if self.rdn_model is not None:
    I_clean = reconstruct(self.rdn_model, I_channels, self.device)
else:
    I_clean = I_channels  # fallback for CPU-only / no weights
```

`run_with_visualization()` adds a "2.5 RDN重建" visualization step showing the denoised I0 channel.

### 4. `backend/app/main.py` — MODIFY

Lifespan loads RDN model and injects into PipelineRunner:

```python
from core_engine.reconstructor import load_rdn_model
rdn_weights = resource_path("weights/rdn_polarization.pth")
rdn_model = load_rdn_model(rdn_weights, device)
pipeline_runner = PipelineRunner(yolo, device, model_key, rdn_model)
```

### 5. Weights — COPY

Copy `code/algae_image_v1/weights/rdn_polarization.pth` → `code/algae_image_v2/weights/rdn_polarization.pth`
(Or reference V1's weights path directly. Copy is safer for exe packaging.)

### 6. `core_engine/polarization_sim.py` (in V2 — hsv_polarization.py) — PRESERVE

Keep `hsv_polarization.py` as-is for fallback/comparison. `polarization_sim.py` becomes the structure tensor version.

## Speed Optimization

- Pipeline downsamples input to max 1280px wide before processing
- Structure tensor at 1280px: ~100ms (Sobel + GaussianBlur)
- RDN inference at 1280px: ~300ms (0.6M params, fully convolutional)
- YOLOv8s at 640px: ~100ms (internal resize)
- **Target**: 0.5–1.0 fps (acceptable for demo)

## Non-Goals

- No YOLO retraining (use existing v8s weights)
- No frontend changes
- No changes to camera/video controllers
- No changes to stream_state or live monitor endpoints

## Rollback

Set `SKIP_RDN=True` and `DEFAULT_MODEL="v8l"` in config to revert to HSV pipeline.
Keep `hsv_polarization.py` as backup implementation.
