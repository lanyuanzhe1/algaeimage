"""HSV Pipeline Evaluation — No RDN (Skip Reconstruction).

Pipeline: RGB → HSV polarization sim → I_enh v2 → YOLOv8l → evaluation

This variant SKIPS the RDN reconstruction step entirely. The HSV polarization
simulation produces 4 channels (I0/I45/I90/I135) directly from RGB color
mapping. I_enh v2 processes these channels to generate the enhanced grayscale
image for YOLO detection.

Rationale: The HSV→polarization mapping (Hue→AoP, Saturation→DoLP, Value→S0)
is a deterministic color-space transform, not a noisy physical measurement.
Unlike the structure-tensor method (which adds synthetic noise requiring RDN
denoising), the HSV output is inherently smooth — making RDN unnecessary.

Compared to: evaluate_pipeline.py (which includes tiled RDN reconstruction).
"""

import sys
from pathlib import Path
import json
import time
from collections import defaultdict

import numpy as np
import cv2
from tqdm import tqdm
import torch
from ultralytics import YOLO

# ── Paths ─────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / "Polar_sim_0520"))
from hsv_polarization import hsv_to_polarization

# ── Config ─────────────────────────────────────────────────────────
FMPD_IMAGES = Path("E:/code/codex/code/algae_guardian/data/download/extracted/dataset/dataset")
FMPD_LABELS = Path("E:/code/codex/code/algae_guardian/data/fmpd_rdn_output/labels")
YOLO_WEIGHTS = Path("E:/code/codex/code/Polar_sim_0520/output/yolo_training_hsv/v8l_hsv/weights/best.pt")

CLASS_NAMES = ["Other-phytoplankton", "Non-phytoplankton",
               "Woronichinia", "Spiroides", "Dinobryon"]

# I_enh v2 parameters (same as v1)
ALPHA = 0.6
BETA = 0.25
GAMMA = 0.35
CONF_THRESHOLD = 0.25

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {DEVICE}")


# ── I_enh v2 (no-RDN variant) ─────────────────────────────────────
def i_enh_v2_direct(pol_channels):
    """Apply I_enh v2 enhancement directly on HSV polarization channels.

    Unlike the v1 version, this computes DoLP/AoP from the RAW HSV-simulated
    channels without RDN pre-processing. The HSV output is already smooth
    (deterministic color mapping), so Stokes parameters are well-behaved.

    Args:
        pol_channels: dict with keys I0, I45, I90, I135 (uint8 H×W)

    Returns:
        (H, W) uint8 enhanced grayscale image
    """
    I0 = pol_channels["I0"].astype(np.float32) / 255.0
    I45 = pol_channels["I45"].astype(np.float32) / 255.0
    I90 = pol_channels["I90"].astype(np.float32) / 255.0
    I135 = pol_channels["I135"].astype(np.float32) / 255.0

    S0 = I0 + I90
    S1 = I0 - I90
    S2 = I45 - I135
    DoLP = np.sqrt(S1 ** 2 + S2 ** 2) / (S0 + 1e-8)
    AoP = 0.5 * np.arctan2(S2, S1)

    # I_enh v2 formula:
    # I_enh = S0 × (1 + α − γ·DoLP + β·|sin(2·AoP)|·DoLP)
    sin_2aop = np.abs(np.sin(2 * AoP))
    I_enh = S0 * (1.0 + ALPHA - GAMMA * DoLP + BETA * sin_2aop * DoLP)
    I_enh = np.clip(I_enh, 0, 1)
    return (I_enh * 255).astype(np.uint8)


# ── Metrics (same as evaluate_pipeline.py) ─────────────────────────
def box_iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / (area_a + area_b - inter + 1e-10)


def compute_ap(precisions, recalls):
    ap = 0.0
    for t in np.linspace(0, 1, 11):
        p_at_t = max([p for p, r in zip(precisions, recalls) if r >= t], default=0)
        ap += p_at_t / 11.0
    return ap


def evaluate_mAP(gt_boxes_per_image, pred_boxes_per_image, iou_thresh=0.5):
    """Compute per-class and overall mAP50."""
    all_classes = set()
    for gts in gt_boxes_per_image.values():
        for g in gts: all_classes.add(g[0])
    for preds in pred_boxes_per_image.values():
        for p in preds: all_classes.add(p[0])

    ap_per_class = {}
    for cls_id in sorted(all_classes):
        preds_cls = []
        for img_key, preds in pred_boxes_per_image.items():
            for p in preds:
                if p[0] == cls_id:
                    preds_cls.append((img_key, p[1:5], p[5]))

        preds_cls.sort(key=lambda x: x[2], reverse=True)

        total_gt = sum(1 for gts in gt_boxes_per_image.values()
                       for g in gts if g[0] == cls_id)

        if total_gt == 0:
            ap_per_class[cls_id] = 0.0
            continue

        tp = np.zeros(len(preds_cls))
        fp = np.zeros(len(preds_cls))
        gt_matched = defaultdict(set)

        for i, (img_key, bbox, conf) in enumerate(preds_cls):
            gts = gt_boxes_per_image.get(img_key, [])
            gts_cls = [(j, g) for j, g in enumerate(gts) if g[0] == cls_id]

            best_iou, best_j = 0, -1
            for j, g in gts_cls:
                if j in gt_matched[img_key]:
                    continue
                iou = box_iou(bbox, g[1:5])
                if iou > best_iou:
                    best_iou, best_j = iou, j

            if best_iou >= iou_thresh and best_j not in gt_matched[img_key]:
                tp[i] = 1
                gt_matched[img_key].add(best_j)
            else:
                fp[i] = 1

        tp_cum = np.cumsum(tp); fp_cum = np.cumsum(fp)
        recalls = tp_cum / total_gt if total_gt > 0 else np.zeros_like(tp_cum)
        precisions = tp_cum / (tp_cum + fp_cum + 1e-10)
        ap_per_class[cls_id] = compute_ap(precisions, recalls)

    mAP50 = np.mean(list(ap_per_class.values())) if ap_per_class else 0
    return ap_per_class, mAP50


# ── Main Pipeline ──────────────────────────────────────────────────
def main():
    yolo = YOLO(str(YOLO_WEIGHTS))
    yolo.to(DEVICE)
    print(f"YOLO loaded: {YOLO_WEIGHTS}")

    image_files = sorted(FMPD_IMAGES.glob("*.tif"))
    valid_images = [f for f in image_files
                    if (FMPD_LABELS / f"{f.stem}.txt").exists()]
    print(f"Images with labels: {len(valid_images)}/{len(image_files)}")

    gt_boxes = {}
    pred_boxes = {}
    total_time = 0.0
    total_dets = 0
    total_gt_boxes = 0

    for img_path in tqdm(valid_images, desc="Pipeline (no RDN)"):
        stem = img_path.stem

        # ── Ground truth ─────────────────────────────────────
        gts = []
        img_bgr = cv2.imread(str(img_path))
        ih, iw = img_bgr.shape[:2]
        with open(FMPD_LABELS / f"{stem}.txt") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) >= 5:
                    cls_id = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:5])
                    x1 = (cx - w / 2) * iw
                    y1 = (cy - h / 2) * ih
                    x2 = (cx + w / 2) * iw
                    y2 = (cy + h / 2) * ih
                    gts.append((cls_id, x1, y1, x2, y2))
        gt_boxes[stem] = gts
        total_gt_boxes += len(gts)

        # ── Pipeline (3 steps, no RDN) ───────────────────────
        t0 = time.time()

        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # Step 1: HSV polarization simulation
        #   H → AoP, S → DoLP, V → S0 → 4-channel I(θ)
        pol = hsv_to_polarization(rgb, polarization_strength=1.0,
                                  add_noise=False)

        # Step 2: I_enh v2 — directly from HSV channels (NO RDN)
        enhanced = i_enh_v2_direct(pol)

        # Step 3: YOLOv8l detection
        I_3ch = np.stack([enhanced, enhanced, enhanced], axis=-1)
        results = yolo.predict(I_3ch, conf=CONF_THRESHOLD, imgsz=640,
                               device=DEVICE, verbose=False)

        elapsed = time.time() - t0
        total_time += elapsed

        # Parse predictions
        preds = []
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                xyxy = boxes.xyxy[i].tolist()
                preds.append((cls_id, xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf))
        pred_boxes[stem] = preds
        total_dets += len(preds)

    # ── Evaluate ──────────────────────────────────────────────
    ap_per_class, mAP50 = evaluate_mAP(gt_boxes, pred_boxes)

    print(f"\n{'='*65}")
    print(f"  HSV Pipeline (NO RDN) — FMPD 5-Class")
    print(f"{'='*65}")
    print(f"  Images:            {len(valid_images)}")
    print(f"  Avg pipeline time: {total_time/len(valid_images):.3f}s/image")
    print(f"  Total detections:  {total_dets}")
    print(f"  GT boxes:          {total_gt_boxes}")
    print(f"  YOLO weights:      {YOLO_WEIGHTS.name}")
    print(f"\n  {'Class':<25s} | {'mAP50':>8s}")
    print(f"  {'-'*25} | {'-'*8}")

    for cls_id in range(len(CLASS_NAMES)):
        name = CLASS_NAMES[cls_id]
        ap = ap_per_class.get(cls_id, 0)
        print(f"  {name:<25s} | {ap:8.4f}")

    print(f"  {'-'*25} | {'-'*8}")
    print(f"  {'OVERALL':<25s} | {mAP50:8.4f}")

    # ── Save report ──────────────────────────────────────────
    report = {
        "pipeline": "HSV_no_RDN",
        "mAP50": float(mAP50),
        "per_class": {
            CLASS_NAMES[c]: float(ap_per_class.get(c, 0))
            for c in range(len(CLASS_NAMES))
        },
        "num_images": len(valid_images),
        "total_detections": total_dets,
        "total_gt_boxes": total_gt_boxes,
        "avg_time_s": round(total_time / len(valid_images), 3),
        "device": DEVICE,
        "yolo_weights": str(YOLO_WEIGHTS),
        "note": "HSV polarization → I_enh v2 → YOLOv8l. NO RDN reconstruction.",
    }
    report_path = BASE / "evaluation_report_no_rdn.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
