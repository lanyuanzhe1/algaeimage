"""Full HSV pipeline evaluation on FMPD dataset.

Pipeline: RGB → HSV polarization sim → HSV RDN → I_enh v2 → YOLOv8l → evaluation

Reports per-class and overall metrics against FMPD ground truth labels.
"""
import sys
import os
from pathlib import Path

# Add required paths
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / "Polar_sim_0520"))
sys.path.insert(0, str(BASE.parent / "algae_image_v1" / "core_engine"))

import json
import time
import numpy as np
import cv2
from collections import defaultdict
from tqdm import tqdm

import torch
from ultralytics import YOLO

from models import RDN
from hsv_polarization import hsv_to_polarization

# ── Config ────────────────────────────────────────────────────────
FMPD_IMAGES = Path("E:/code/codex/code/algae_guardian/data/download/extracted/dataset/dataset")
FMPD_LABELS = Path("E:/code/codex/code/algae_guardian/data/fmpd_rdn_output/labels")
RDN_WEIGHTS = BASE / "checkpoint" / "best.pth"
YOLO_WEIGHTS = Path("E:/code/codex/code/Polar_sim_0520/output/yolo_training_hsv/v8l_hsv/weights/best.pt")

CLASS_NAMES = ["Other-phytoplankton", "Non-phytoplankton",
               "Woronichinia", "Spiroides", "Dinobryon"]

# I_enh v2 parameters
ALPHA, BETA, GAMMA = 0.6, 0.25, 0.35
CONF_THRESHOLD = 0.25

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {DEVICE}")


# ── Load models ───────────────────────────────────────────────────
def load_rdn(weights_path):
    model = RDN(num_channels=4, num_features=16, growth_rate=16,
                num_blocks=12, num_layers=6).to(DEVICE)
    state = torch.load(weights_path, map_location=DEVICE)
    # Handle 'module.' prefix from DataParallel
    from collections import OrderedDict
    new_state = OrderedDict()
    for k, v in state.items():
        new_state[k.replace("module.", "")] = v
    model.load_state_dict(new_state)
    model.eval()
    print(f"RDN loaded: {sum(p.numel() for p in model.parameters()):,} params")
    return model


def i_enh_v2(rgb, channels):
    """Apply I_enh v2 enhancement. Returns enhanced grayscale (H,W) uint8."""
    I0 = channels["I0"].astype(np.float32) / 255.0
    I45 = channels["I45"].astype(np.float32) / 255.0
    I90 = channels["I90"].astype(np.float32) / 255.0
    I135 = channels["I135"].astype(np.float32) / 255.0

    S0 = I0 + I90
    S1 = I0 - I90
    S2 = I45 - I135
    DoLP = np.sqrt(S1 ** 2 + S2 ** 2) / (S0 + 1e-8)
    AoP = 0.5 * np.arctan2(S2, S1)

    I_enh = S0 * (1.0 + ALPHA - GAMMA * DoLP + BETA * np.abs(np.sin(2 * AoP)) * DoLP)
    I_enh = np.clip(I_enh, 0, 1)
    return (I_enh * 255).astype(np.uint8)


def rdn_reconstruct(model, channels, tile_size=512, overlap=32):
    """Tiled RDN reconstruction to handle large images on limited GPU memory."""
    h, w = channels["I0"].shape

    x = np.zeros((4, h, w), dtype=np.float32)
    x[0] = channels["I0"].astype(np.float32) / 255.0
    x[1] = channels["I45"].astype(np.float32) / 255.0
    x[2] = channels["I90"].astype(np.float32) / 255.0
    x[3] = channels["I135"].astype(np.float32) / 255.0

    out = np.zeros((4, h, w), dtype=np.float32)
    weight = np.zeros((h, w), dtype=np.float32)

    stride = tile_size - overlap

    for y0 in range(0, h, stride):
        for x0 in range(0, w, stride):
            y1 = min(y0 + tile_size, h)
            x1 = min(x0 + tile_size, w)

            # Extract tile with padding if needed
            th = y1 - y0
            tw = x1 - x0
            tile = x[:, y0:y1, x0:x1]
            tensor = torch.from_numpy(tile).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                tile_out = model(tensor).squeeze(0).cpu().numpy()

            # Create blend mask for smooth overlap
            mask = np.ones((th, tw), dtype=np.float32)
            if y0 > 0:
                fade = np.linspace(0, 1, min(overlap, th))[:, np.newaxis]
                mask[:len(fade)] *= fade
            if y1 < h:
                fade = np.linspace(1, 0, min(overlap, th))[::-1][:, np.newaxis]
                mask[-len(fade):] *= fade
            if x0 > 0:
                fade = np.linspace(0, 1, min(overlap, tw))
                mask[:, :len(fade)] *= fade
            if x1 < w:
                fade = np.linspace(1, 0, min(overlap, tw))[::-1]
                mask[:, -len(fade):] *= fade

            out[:, y0:y1, x0:x1] += np.clip(tile_out, 0, 1) * mask
            weight[y0:y1, x0:x1] += mask

    # Normalize by blend weights
    out /= (weight + 1e-10)

    result = {}
    for i, key in enumerate(["I0", "I45", "I90", "I135"]):
        result[key] = (np.clip(out[i], 0, 1) * 255).astype(np.uint8)

    S0 = out[0] + out[2]
    S1 = out[0] - out[2]
    S2 = out[1] - out[3]
    result["S0"] = (np.clip(S0, 0, 1) * 255).astype(np.uint8)
    result["DoLP"] = (np.clip(np.sqrt(S1**2 + S2**2) / (S0 + 1e-8), 0, 1) * 255).astype(np.uint8)

    return result


# ── Metrics ────────────────────────────────────────────────────────
def box_iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / (area_a + area_b - inter + 1e-10)


def compute_ap(precisions, recalls):
    """11-point interpolated AP."""
    ap = 0.0
    for t in np.linspace(0, 1, 11):
        p_at_t = max([p for p, r in zip(precisions, recalls) if r >= t], default=0)
        ap += p_at_t / 11.0
    return ap


def evaluate(gt_boxes_per_image, pred_boxes_per_image, iou_thresh=0.5):
    """Compute per-class and overall mAP50."""
    all_classes = set()
    for gts in gt_boxes_per_image.values():
        for g in gts: all_classes.add(g[0])
    for preds in pred_boxes_per_image.values():
        for p in preds: all_classes.add(p[0])

    ap_per_class = {}
    for cls_id in sorted(all_classes):
        # Collect all predictions for this class across images
        preds_cls = []
        for img_key, preds in pred_boxes_per_image.items():
            for p in preds:
                if p[0] == cls_id:
                    preds_cls.append((img_key, p[1:5], p[5]))  # (img, bbox, conf)

        # Sort by confidence descending
        preds_cls.sort(key=lambda x: x[2], reverse=True)

        # Count total GT for this class
        total_gt = sum(1 for gts in gt_boxes_per_image.values()
                       for g in gts if g[0] == cls_id)

        if total_gt == 0 and len(preds_cls) == 0:
            ap_per_class[cls_id] = 0.0
            continue
        if total_gt == 0:
            ap_per_class[cls_id] = 0.0
            continue

        tp = np.zeros(len(preds_cls))
        fp = np.zeros(len(preds_cls))
        gt_matched = defaultdict(set)  # img_key -> set of matched gt indices

        for i, (img_key, bbox, conf) in enumerate(preds_cls):
            gts = gt_boxes_per_image.get(img_key, [])
            gts_cls = [(j, g) for j, g in enumerate(gts) if g[0] == cls_id]

            best_iou = 0; best_j = -1
            for j, g in gts_cls:
                if j in gt_matched[img_key]:
                    continue
                iou = box_iou(bbox, g[1:5])
                if iou > best_iou:
                    best_iou = iou; best_j = j

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


# ── Main ───────────────────────────────────────────────────────────
def main():
    rdn = load_rdn(RDN_WEIGHTS)
    yolo = YOLO(str(YOLO_WEIGHTS))
    yolo.to(DEVICE)
    print(f"YOLO loaded: {YOLO_WEIGHTS}")

    # Collect images with labels
    image_files = sorted(FMPD_IMAGES.glob("*.tif"))
    valid_images = [f for f in image_files
                    if (FMPD_LABELS / f"{f.stem}.txt").exists()]
    print(f"Images with labels: {len(valid_images)}/{len(image_files)}")

    gt_boxes = {}
    pred_boxes = {}
    total_time = 0
    total_dets = 0
    total_gt_boxes = 0

    for img_path in tqdm(valid_images, desc="Pipeline evaluation"):
        stem = img_path.stem

        # Load ground truth
        gts = []
        with open(FMPD_LABELS / f"{stem}.txt") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) >= 5:
                    cls_id = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:5])
                    # Convert YOLO (cx,cy,w,h) normalized to pixel xyxy
                    img = cv2.imread(str(img_path))
                    ih, iw = img.shape[:2]
                    x1 = (cx - w/2) * iw
                    y1 = (cy - h/2) * ih
                    x2 = (cx + w/2) * iw
                    y2 = (cy + h/2) * ih
                    gts.append((cls_id, x1, y1, x2, y2))
        gt_boxes[stem] = gts
        total_gt_boxes += len(gts)

        # ── Pipeline ──────────────────────────────────────
        t0 = time.time()

        rgb = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)

        # Step 1: HSV polarization simulation
        pol = hsv_to_polarization(rgb, polarization_strength=1.0,
                                  add_noise=False)

        # Step 2: RDN reconstruction
        rdn_out = rdn_reconstruct(rdn, pol)

        # Step 3: I_enh v2
        enhanced = i_enh_v2(rgb, rdn_out)

        # Step 4: YOLO detection
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

    # ── Evaluation ───────────────────────────────────────
    ap_per_class, mAP50 = evaluate(gt_boxes, pred_boxes)

    print(f"\n{'='*65}")
    print(f"  HSV Pipeline Evaluation — FMPD 5-Class")
    print(f"{'='*65}")
    print(f"  Images: {len(valid_images)}")
    print(f"  Avg pipeline time: {total_time/len(valid_images):.3f}s/image")
    print(f"  Total detections: {total_dets}, GT boxes: {total_gt_boxes}")
    print(f"\n  {'Class':<25s} | {'mAP50':>8s}")
    print(f"  {'-'*25} | {'-'*8}")

    for cls_id in range(5):
        name = CLASS_NAMES[cls_id]
        ap = ap_per_class.get(cls_id, 0)
        print(f"  {name:<25s} | {ap:8.4f}")

    print(f"  {'-'*25} | {'-'*8}")
    print(f"  {'OVERALL':<25s} | {mAP50:8.4f}")
    print(f"\n  Device: {DEVICE}")
    print(f"  RDN: {RDN_WEIGHTS}")
    print(f"  YOLO: {YOLO_WEIGHTS.name}")

    # Save report
    report = {
        "mAP50": float(mAP50),
        "per_class": {CLASS_NAMES[c]: float(ap_per_class.get(c, 0)) for c in range(5)},
        "num_images": len(valid_images),
        "total_detections": total_dets,
        "total_gt_boxes": total_gt_boxes,
        "avg_time_s": total_time / len(valid_images),
        "device": DEVICE,
        "rdn_weights": str(RDN_WEIGHTS),
        "yolo_weights": str(YOLO_WEIGHTS),
    }
    report_path = BASE / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
