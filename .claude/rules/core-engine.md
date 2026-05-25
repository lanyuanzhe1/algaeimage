---
paths: code/algae_image_v1/core_engine/**
---

# Core Engine Rules

## Zero-framework constraint

- **No FastAPI, no database, no web imports.** Only `numpy`, `PyTorch`, `cv2`, `Pillow`.
- Must remain importable by PyInstaller or C++ bindings — pure computation library.
- All functions are synchronous (no `async/await`).

## Immutable pipeline order

```
RGB原图 → 结构张量偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh v2去散射增强 → YOLOv8s检测(95类)
```

NEVER reorder, skip, or insert stages. This order is physically derived.

## Module responsibilities

| Module | Input | Output | Key detail |
|--------|-------|--------|------------|
| `polarization_sim.py` | RGB image (H,W,3) | 4-channel polarization (I0,I45,I90,I135) | Structure tensor gradient + Malus law |
| `reconstructor.py` | 4-channel polarization | 4-channel enhanced (I0,I45,I90,I135) | RDN: 4→16→16→4, 12 blocks, 6 layers, ~0.6M params |
| `enhancement.py` | Stokes params | Enhanced RGB | I_enh v2: `S0*(1+α-γ·DoLP+β·\|sin(2·AoP)\|·DoLP)` |
| `inference.py` | Enhanced image | Detections with 95 class labels | YOLOv8s wrapper |
| `config.py` | - | - | 95 class names, risk levels (high/medium/low), thresholds |
| `quality.py` | DoLP + SNR + dynamic range | Q score (0-1) | Quality assessment |

## Design invariants

- **I135 is independently computed** — NOT the average of I0/I90. All 4 channels use the same Malus physical model independently, preserving physical meaning of S2 = I45 - I135.
- **Grayscale-dominant input to YOLO** — shape/structure features matter more than color.
- **YOLO training must disable HSV augmentation** (`hsv_s=0.0, hsv_v=0.0`) to preserve polarization channel physics.

## NEVER

- Import `fastapi`, `aiosqlite`, or any web/db library
- Change the pipeline order
- Use I135 = (I0+I90)/2 — physically incorrect
- Add new external dependencies without updating `requirements.txt`
