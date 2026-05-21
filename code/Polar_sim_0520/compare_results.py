"""Compare HSV vs Structure-Tensor YOLO results against FMPD ground truth.

Computes per-class precision, recall, F1, and detection statistics.
Uses IoU > 0.5 matching.
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
GT_DIR = BASE.parent / "algae_guardian" / "data" / "fmpd_rdn_output" / "labels"
HSV_DIR = OUTPUT / "yolo_labels_hsv"
STRUCT_DIR = OUTPUT / "yolo_labels_struct"

CLASS_NAMES = ["Other-phytoplankton", "Non-phytoplankton",
               "Woronichinia", "Spiroides", "Dinobryon"]
IOU_THRESH = 0.5


def load_yolo_labels(label_dir: Path) -> dict:
    """Load YOLO-format labels. Returns {stem: [(cls, cx, cy, w, h, conf), ...]}."""
    labels = {}
    for f in sorted(label_dir.glob("*.txt")):
        stem = f.stem
        dets = []
        with open(f) as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                cls_id = int(parts[0])
                cx, cy, w, h = map(float, parts[1:5])
                conf = float(parts[5]) if len(parts) > 5 else 1.0
                dets.append((cls_id, cx, cy, w, h, conf))
        labels[stem] = dets
    return labels


def xywh_to_xyxy(cx, cy, w, h):
    """Convert normalized cxcywh to pixel xyxy."""
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def box_iou(a, b):
    """IoU of two [x1, y1, x2, y2] boxes."""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / (area_a + area_b - inter + 1e-10)


def match_detections(gt_boxes, pred_boxes, iou_thresh=0.5):
    """Match predictions to ground truth using greedy IoU matching.

    Args:
        gt_boxes: list of (cls_id, x1, y1, x2, y2) normalized [0,1]
        pred_boxes: list of (cls_id, x1, y1, x2, y2, conf)

    Returns:
        tp_per_class, fp_per_class, fn_per_class, matched pairs
    """
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)

    # Count ground truth per class
    gt_by_class = defaultdict(list)
    for i, (cls_id, *box) in enumerate(gt_boxes):
        gt_by_class[cls_id].append((i, cls_id, *box))

    # Count FN = all GT boxes that exist
    for cls_id, items in gt_by_class.items():
        fn[cls_id] += len(items)

    # Match predictions to ground truths
    pred_by_class = defaultdict(list)
    for i, (cls_id, *box_conf) in enumerate(pred_boxes):
        pred_by_class[cls_id].append((i, cls_id, *box_conf))

    for cls_id in set(list(gt_by_class.keys()) + list(pred_by_class.keys())):
        gts = gt_by_class.get(cls_id, [])
        preds = pred_by_class.get(cls_id, [])

        if not preds:
            # All GT unmatched = all FN
            continue  # fn already counted

        if not gts:
            # All predictions are FP
            fp[cls_id] += len(preds)
            continue

        # Build IoU matrix
        iou_matrix = np.zeros((len(gts), len(preds)))
        for i, (g_idx, g_cls, gx1, gy1, gx2, gy2) in enumerate(gts):
            for j, (p_idx, p_cls, px1, py1, px2, py2, conf) in enumerate(preds):
                iou_matrix[i, j] = box_iou([gx1, gy1, gx2, gy2],
                                           [px1, py1, px2, py2])

        # Greedy matching: match highest IoU pairs
        matched_gt = set()
        matched_pred = set()

        while True:
            if iou_matrix.size == 0:
                break
            max_idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
            max_iou = iou_matrix[max_idx]

            if max_iou < iou_thresh:
                break

            gt_i, pred_i = max_idx
            matched_gt.add(gts[gt_i][0])
            matched_pred.add(preds[pred_i][0])
            tp[cls_id] += 1

            # Remove matched row/col
            iou_matrix[gt_i, :] = -1
            iou_matrix[:, pred_i] = -1

        # Unmatched predictions = FP
        fp[cls_id] += len(preds) - len(matched_pred)
        # FN already counted at class level, adjust for matched
        fn[cls_id] -= len(matched_gt)

    return dict(tp), dict(fp), dict(fn)


def compute_metrics(tp, fp, fn):
    """Compute precision, recall, F1 per class."""
    metrics = {}
    all_classes = set(list(tp.keys()) + list(fp.keys()) + list(fn.keys()))

    for cls_id in sorted(all_classes):
        tp_c = tp.get(cls_id, 0)
        fp_c = fp.get(cls_id, 0)
        fn_c = fn.get(cls_id, 0)

        precision = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
        recall = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics[cls_id] = {
            "tp": tp_c, "fp": fp_c, "fn": fn_c,
            "precision": precision, "recall": recall, "f1": f1,
        }
    return metrics


def main():
    print("Loading labels...")
    gt = load_yolo_labels(GT_DIR)
    hsv = load_yolo_labels(HSV_DIR)
    struct = load_yolo_labels(STRUCT_DIR)

    # All should have the same stems
    stems = sorted(set(gt.keys()) & set(hsv.keys()) & set(struct.keys()))
    print(f"Common images: {len(stems)}")

    # ── Per-image matching ──────────────────────────
    hsv_tp = defaultdict(int); hsv_fp = defaultdict(int); hsv_fn = defaultdict(int)
    struct_tp = defaultdict(int); struct_fp = defaultdict(int); struct_fn = defaultdict(int)

    hsv_det_counts = []; struct_det_counts = []; gt_det_counts = []
    hsv_conf = []; struct_conf = []

    for stem in stems:
        gt_boxes_xyxy = []
        for cls_id, cx, cy, w, h, conf in gt[stem]:
            xyxy = xywh_to_xyxy(cx, cy, w, h)
            gt_boxes_xyxy.append((cls_id, *xyxy))

        hsv_boxes_xyxy = []
        for cls_id, cx, cy, w, h, conf in hsv[stem]:
            xyxy = xywh_to_xyxy(cx, cy, w, h)
            hsv_boxes_xyxy.append((cls_id, *xyxy, conf))
            hsv_conf.append(conf)

        struct_boxes_xyxy = []
        for cls_id, cx, cy, w, h, conf in struct[stem]:
            xyxy = xywh_to_xyxy(cx, cy, w, h)
            struct_boxes_xyxy.append((cls_id, *xyxy, conf))
            struct_conf.append(conf)

        # Match
        h_tp, h_fp, h_fn = match_detections(gt_boxes_xyxy, hsv_boxes_xyxy, IOU_THRESH)
        s_tp, s_fp, s_fn = match_detections(gt_boxes_xyxy, struct_boxes_xyxy, IOU_THRESH)

        for k, v in h_tp.items(): hsv_tp[k] += v
        for k, v in h_fp.items(): hsv_fp[k] += v
        for k, v in h_fn.items(): hsv_fn[k] += v
        for k, v in s_tp.items(): struct_tp[k] += v
        for k, v in s_fp.items(): struct_fp[k] += v
        for k, v in s_fn.items(): struct_fn[k] += v

        hsv_det_counts.append(len(hsv_boxes_xyxy))
        struct_det_counts.append(len(struct_boxes_xyxy))
        gt_det_counts.append(len(gt_boxes_xyxy))

    # ── Metrics ─────────────────────────────────────
    hsv_metrics = compute_metrics(hsv_tp, hsv_fp, hsv_fn)
    struct_metrics = compute_metrics(struct_tp, struct_fp, struct_fn)

    # ── Report ──────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  YOLO Detection Comparison: HSV vs Structure Tensor")
    print(f"{'='*80}")
    print(f"  Images: {len(stems)} | IoU threshold: {IOU_THRESH}")
    print(f"  GT annotations: {sum(gt_det_counts)} | HSV detections: {sum(hsv_det_counts)} | Struct detections: {sum(struct_det_counts)}")
    print()

    # Header
    header = f"{'Class':<25s} | {'HSV Prec':>8s} {'HSV Rec':>8s} {'HSV F1':>8s} | {'Struct Prec':>8s} {'Struct Rec':>8s} {'Struct F1':>8s} | {'GT Count':>8s}"
    sep = "-" * len(header)
    print(header)
    print(sep)

    total = {"hsv_tp": 0, "hsv_fp": 0, "hsv_fn": 0, "struct_tp": 0, "struct_fp": 0, "struct_fn": 0}

    for cls_id in range(len(CLASS_NAMES)):
        h = hsv_metrics.get(cls_id, {"precision": 0, "recall": 0, "f1": 0, "tp": 0, "fp": 0, "fn": 0})
        s = struct_metrics.get(cls_id, {"precision": 0, "recall": 0, "f1": 0, "tp": 0, "fp": 0, "fn": 0})
        gt_count = sum(1 for stem in stems for d in gt[stem] if d[0] == cls_id)

        print(f"{CLASS_NAMES[cls_id]:<25s} | {h['precision']:8.4f} {h['recall']:8.4f} {h['f1']:8.4f} | {s['precision']:8.4f} {s['recall']:8.4f} {s['f1']:8.4f} | {gt_count:8d}")

        for k in ["tp", "fp", "fn"]:
            total[f"hsv_{k}"] += h[k]
            total[f"struct_{k}"] += s[k]

    print(sep)

    # Overall
    h_prec = total["hsv_tp"] / (total["hsv_tp"] + total["hsv_fp"]) if (total["hsv_tp"] + total["hsv_fp"]) > 0 else 0
    h_rec = total["hsv_tp"] / (total["hsv_tp"] + total["hsv_fn"]) if (total["hsv_tp"] + total["hsv_fn"]) > 0 else 0
    h_f1 = 2 * h_prec * h_rec / (h_prec + h_rec) if (h_prec + h_rec) > 0 else 0

    s_prec = total["struct_tp"] / (total["struct_tp"] + total["struct_fp"]) if (total["struct_tp"] + total["struct_fp"]) > 0 else 0
    s_rec = total["struct_tp"] / (total["struct_tp"] + total["struct_fn"]) if (total["struct_tp"] + total["struct_fn"]) > 0 else 0
    s_f1 = 2 * s_prec * s_rec / (s_prec + s_rec) if (s_prec + s_rec) > 0 else 0

    print(f"{'OVERALL':<25s} | {h_prec:8.4f} {h_rec:8.4f} {h_f1:8.4f} | {s_prec:8.4f} {s_rec:8.4f} {s_f1:8.4f} | {sum(gt_det_counts):8d}")

    # ── Detection stats ─────────────────────────────
    print(f"\n{'='*80}")
    print(f"  Detection Statistics")
    print(f"{'='*80}")
    print(f"  HSV:       {sum(hsv_det_counts):5d} detections, {np.mean(hsv_det_counts):.1f}/img, conf mean={np.mean(hsv_conf):.3f}")
    print(f"  Struct:    {sum(struct_det_counts):5d} detections, {np.mean(struct_det_counts):.1f}/img, conf mean={np.mean(struct_conf):.3f}")
    print(f"  GT:        {sum(gt_det_counts):5d} annotations, {np.mean(gt_det_counts):.1f}/img")

    # Images with no detections
    hsv_empty = sum(1 for stem in stems if len(hsv[stem]) == 0)
    struct_empty = sum(1 for stem in stems if len(struct[stem]) == 0)
    print(f"  Empty img: HSV={hsv_empty}, Struct={struct_empty}")

    # Win/tie/loss
    print(f"\n  Winner per class:")
    for cls_id in range(len(CLASS_NAMES)):
        h = hsv_metrics.get(cls_id, {})
        s = struct_metrics.get(cls_id, {})
        if h.get("f1", 0) > s.get("f1", 0):
            winner = "HSV"
        elif s.get("f1", 0) > h.get("f1", 0):
            winner = "Struct"
        else:
            winner = "TIE"
        print(f"    {CLASS_NAMES[cls_id]:<25s}: {winner:>6s}  (HSV F1={h.get('f1',0):.4f}, Struct F1={s.get('f1',0):.4f})")

    # ── Save JSON ───────────────────────────────────
    report = {
        "config": {"iou_threshold": IOU_THRESH, "num_images": len(stems)},
        "per_class": {},
        "overall": {
            "hsv": {"precision": h_prec, "recall": h_rec, "f1": h_f1,
                    "tp": total["hsv_tp"], "fp": total["hsv_fp"], "fn": total["hsv_fn"],
                    "total_detections": sum(hsv_det_counts), "empty_images": hsv_empty,
                    "mean_confidence": float(np.mean(hsv_conf))},
            "struct": {"precision": s_prec, "recall": s_rec, "f1": s_f1,
                       "tp": total["struct_tp"], "fp": total["struct_fp"], "fn": total["struct_fn"],
                       "total_detections": sum(struct_det_counts), "empty_images": struct_empty,
                       "mean_confidence": float(np.mean(struct_conf))},
            "ground_truth": {"total_annotations": sum(gt_det_counts)},
        },
    }

    for cls_id in range(len(CLASS_NAMES)):
        h = hsv_metrics.get(cls_id, {})
        s = struct_metrics.get(cls_id, {})
        report["per_class"][CLASS_NAMES[cls_id]] = {
            "hsv": {"precision": h.get("precision", 0), "recall": h.get("recall", 0),
                    "f1": h.get("f1", 0), "tp": h.get("tp", 0),
                    "fp": h.get("fp", 0), "fn": h.get("fn", 0)},
            "struct": {"precision": s.get("precision", 0), "recall": s.get("recall", 0),
                       "f1": s.get("f1", 0), "tp": s.get("tp", 0),
                       "fp": s.get("fp", 0), "fn": s.get("fn", 0)},
        }

    report_path = OUTPUT / "comparison_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
