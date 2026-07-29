"""Full auto pipeline: Train → Evaluate → Compare → Report.

Runs without user intervention. Saves everything to output/yolo_training_hsv/.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # fix OMP conflict OpenCV vs PyTorch

import json
import sys
import time
import numpy as np
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
TRAIN_DIR = OUTPUT / "yolo_training_hsv"
DATASET_YAML = TRAIN_DIR / "dataset.yaml"
HSV_INPUT = OUTPUT / "yolo_input_hsv"
STRUCT_INPUT = Path("E:/code/algaeimage/code/algae_guardian/data/fmpd_rdn_output/images")
GT_LABELS = Path("E:/code/algaeimage/code/algae_guardian/data/fmpd_rdn_output/labels")

CLASS_NAMES = ["Other-phytoplankton", "Non-phytoplankton",
               "Woronichinia", "Spiroides", "Dinobryon"]

EPOCHS = 300; BATCH = 8; IMG_SIZE = 640; PATIENCE = 50


def step1_train():
    """Train YOLOv8l on HSV dataset."""
    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"{'='*55}\nSTEP 1: Train YOLOv8l on HSV dataset\n{'='*55}")
    print(f"Device: {device} | Epochs: {EPOCHS} | Batch: {BATCH}")
    if device == "cuda":
        torch.cuda.empty_cache()

    model = YOLO("yolov8l.pt")
    t0 = time.time()

    results = model.train(
        data=str(DATASET_YAML), epochs=EPOCHS, batch=BATCH, imgsz=IMG_SIZE,
        patience=PATIENCE, lr0=1e-3, lrf=1e-4, optimizer="AdamW",
        device=device, project=str(TRAIN_DIR), name="v8l_hsv",
        exist_ok=True, pretrained=True, seed=0, deterministic=True, amp=True,
        close_mosaic=10, warmup_epochs=5, warmup_momentum=0.8,
        weight_decay=5e-4, workers=0, cache=False, plots=True, save=True, val=True,
        hsv_s=0.0, hsv_v=0.0, fliplr=0.5, mosaic=1.0, mixup=0.1,
        erasing=0.4, auto_augment="randaugment",
    )

    elapsed = time.time() - t0
    info = {
        "best_epoch": getattr(results, "best_epoch", None),
        "best_fitness": getattr(results, "best_fitness", None),
        "train_time_s": elapsed,
    }
    with open(TRAIN_DIR / "train_info.json", "w") as f:
        json.dump(info, f, indent=2)
    print(f"Training done: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    return info


def step2_detect_and_eval():
    """YOLO detection + evaluation for both HSV and Struct models.

    HSV model on HSV images (fair for HSV),
    Struct model on Struct images (fair for Struct).
    """
    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n{'='*55}\nSTEP 2: Evaluate both models\n{'='*55}")

    hsv_model_path = TRAIN_DIR / "v8l_hsv" / "weights" / "best.pt"
    struct_model_path = Path("E:/code/algaeimage/code/algae_guardian/data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/best.pt")

    if not hsv_model_path.exists():
        print(f"HSV model not found at {hsv_model_path}, trying last.pt")
        hsv_model_path = TRAIN_DIR / "v8l_hsv" / "weights" / "last.pt"

    # Load labels
    def load_gt(stems):
        gt = {}
        for s in stems:
            f = GT_LABELS / f"{s}.txt"
            if not f.exists():
                continue
            boxes = []
            for line in open(f):
                p = line.strip().split()
                if len(p) >= 5:
                    boxes.append((int(p[0]), *map(float, p[1:5])))
            gt[s] = boxes
        return gt

    def xywh_to_xyxy(cx, cy, w, h):
        return [cx-w/2, cy-h/2, cx+w/2, cy+h/2]

    def box_iou(a, b):
        x1, y1 = max(a[0], b[0]), max(a[1], b[1])
        x2, y2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0, x2-x1) * max(0, y2-y1)
        area_a = max(0, (a[2]-a[0])*(a[3]-a[1]))
        area_b = max(0, (b[2]-b[0])*(b[3]-b[1]))
        return inter / (area_a + area_b - inter + 1e-10)

    def match_greedy(gt_boxes, pred_boxes, iou_thresh=0.5):
        tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
        gt_by_cls = defaultdict(list)
        for g in gt_boxes:
            gt_by_cls[g[0]].append(g)
        pred_by_cls = defaultdict(list)
        for p in pred_boxes:
            pred_by_cls[p[0]].append(p)
        for cls_id in set(list(gt_by_cls) + list(pred_by_cls)):
            gts = gt_by_cls.get(cls_id, [])
            preds = pred_by_cls.get(cls_id, [])
            fn[cls_id] = len(gts)
            if not preds:
                continue
            if not gts:
                fp[cls_id] += len(preds)
                continue
            ious = np.zeros((len(gts), len(preds)))
            for i, g in enumerate(gts):
                for j, p in enumerate(preds):
                    ious[i,j] = box_iou(xywh_to_xyxy(*g[1:]), xywh_to_xyxy(*p[1:5]))
            matched_gt = set(); matched_pred = set()
            while ious.size > 0:
                idx = np.unravel_index(ious.argmax(), ious.shape)
                if ious[idx] < iou_thresh: break
                tp[cls_id] += 1
                matched_gt.add(idx[0]); matched_pred.add(idx[1])
                ious[idx[0], :] = -1; ious[:, idx[1]] = -1
            fp[cls_id] += len(preds) - len(matched_pred)
            fn[cls_id] -= len(matched_gt)
        return dict(tp), dict(fp), dict(fn)

    def run_eval(model_path, image_dir, gt_stems):
        print(f"  Model: {model_path.name}")
        model = YOLO(str(model_path))
        model.to(device)

        stems = [s for s in gt_stems if (image_dir / f"{s}.jpg").exists()]
        all_tp = defaultdict(int); all_fp = defaultdict(int); all_fn = defaultdict(int)
        total_dets = 0; total_gt = 0

        for i, stem in enumerate(stems):
            results = model.predict(str(image_dir / f"{stem}.jpg"),
                                    conf=0.25, imgsz=640, device=device, verbose=False)
            boxes = results[0].boxes
            preds = []
            if boxes is not None:
                for b in boxes:
                    xyxy = b.xyxy[0].tolist()
                    h, w = results[0].orig_shape
                    cx = ((xyxy[0]+xyxy[2])/2)/w; cy = ((xyxy[1]+xyxy[3])/2)/h
                    bw_px = (xyxy[2]-xyxy[0])/w; bh_px = (xyxy[3]-xyxy[1])/h
                    preds.append((int(b.cls.item()), cx, cy, bw_px, bh_px, float(b.conf.item())))
            total_dets += len(preds)
            gt_boxes = gt.get(stem, [])
            total_gt += len(gt_boxes)
            tp, fp, fn = match_greedy(gt_boxes, preds)
            for k,v in tp.items(): all_tp[k] += v
            for k,v in fp.items(): all_fp[k] += v
            for k,v in fn.items(): all_fn[k] += v

            if device == "cuda" and (i+1) % 100 == 0:
                torch.cuda.empty_cache()

        per_class = {}
        for c in range(len(CLASS_NAMES)):
            tc = all_tp.get(c,0); fpc = all_fp.get(c,0); fnc = all_fn.get(c,0)
            p = tc/(tc+fpc) if (tc+fpc)>0 else 0
            r = tc/(tc+fnc) if (tc+fnc)>0 else 0
            f1 = 2*p*r/(p+r) if (p+r)>0 else 0
            per_class[c] = {"tp":tc,"fp":fpc,"fn":fnc,"precision":p,"recall":r,"f1":f1}
        tp_all = sum(all_tp.values()); fp_all = sum(all_fp.values()); fn_all = sum(all_fn.values())
        p_all = tp_all/(tp_all+fp_all) if (tp_all+fp_all)>0 else 0
        r_all = tp_all/(tp_all+fn_all) if (tp_all+fn_all)>0 else 0
        f1_all = 2*p_all*r_all/(p_all+r_all) if (p_all+r_all)>0 else 0

        print(f"    Dets={total_dets}, GT={total_gt}, Overall F1={f1_all:.4f}")
        return {"per_class": per_class, "overall": {"precision":p_all,"recall":r_all,"f1":f1_all,
                "tp":tp_all,"fp":fp_all,"fn":fn_all,"detections":total_dets,"gt_boxes":total_gt}}

    gt = load_gt([s.stem for s in GT_LABELS.glob("*.txt")])
    gt_stems = list(gt.keys())

    hsv_eval = run_eval(hsv_model_path, HSV_INPUT, gt_stems)
    struct_eval = run_eval(struct_model_path, STRUCT_INPUT, gt_stems)

    return hsv_eval, struct_eval


def step3_report(hsv_eval, struct_eval, train_info):
    """Generate comparison report."""
    print(f"\n{'='*80}")
    print(f"  FAIR COMPARISON: HSV-trained vs Structure-trained YOLOv8l")
    print(f"{'='*80}")
    print(f"  HSV model trained on:  234 HSV-enhanced images, best epoch={train_info.get('best_epoch','?')}")
    print(f"  Struct model trained on: 234 Struct-enhanced images, best epoch=110")
    print(f"  Each model evaluated ON ITS OWN data distribution\n")

    header = f"{'Class':<25s} | {'HSV F1':>8s} {'HSV P':>8s} {'HSV R':>8s} | {'Struct F1':>8s} {'Struct P':>8s} {'Struct R':>8s}"
    print(header)
    print("-" * len(header))

    for c in range(len(CLASS_NAMES)):
        h = hsv_eval["per_class"].get(c, {})
        s = struct_eval["per_class"].get(c, {})
        print(f"{CLASS_NAMES[c]:<25s} | {h.get('f1',0):8.4f} {h.get('precision',0):8.4f} {h.get('recall',0):8.4f} | {s.get('f1',0):8.4f} {s.get('precision',0):8.4f} {s.get('recall',0):8.4f}")

    print("-" * len(header))
    ho = hsv_eval["overall"]
    so = struct_eval["overall"]
    print(f"{'OVERALL':<25s} | {ho['f1']:8.4f} {ho['precision']:8.4f} {ho['recall']:8.4f} | {so['f1']:8.4f} {so['precision']:8.4f} {so['recall']:8.4f}")

    # Count wins
    hsv_wins = sum(1 for c in range(len(CLASS_NAMES))
                   if hsv_eval["per_class"].get(c,{}).get("f1",0) > struct_eval["per_class"].get(c,{}).get("f1",0))
    struct_wins = sum(1 for c in range(len(CLASS_NAMES))
                      if struct_eval["per_class"].get(c,{}).get("f1",0) > hsv_eval["per_class"].get(c,{}).get("f1",0))
    print(f"\nWinner: HSV={hsv_wins}/5, Struct={struct_wins}/5")
    print(f"HSV detections: {ho['detections']}, GT: {ho['gt_boxes']}")
    print(f"Struct detections: {so['detections']}, GT: {so['gt_boxes']}")

    # Save report
    report = {
        "hsv": {"per_class": {CLASS_NAMES[c]: hsv_eval["per_class"].get(c,{}) for c in range(5)},
                "overall": ho},
        "struct": {"per_class": {CLASS_NAMES[c]: struct_eval["per_class"].get(c,{}) for c in range(5)},
                   "overall": so},
        "training": train_info,
    }
    with open(OUTPUT / "fair_comparison_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {OUTPUT / 'fair_comparison_report.json'}")


if __name__ == "__main__":
    train_info = step1_train()
    hsv_eval, struct_eval = step2_detect_and_eval()
    step3_report(hsv_eval, struct_eval, train_info)
    print("\nALL DONE.")
