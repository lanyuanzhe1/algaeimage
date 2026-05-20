"""Stage 4: YOLOv8l detection on HSV-enhanced images.

Input:  output/yolo_input_hsv/
Model:  best.pt (YOLOv8l, 5 classes, mAP50=0.429)
Output: output/yolo_results_hsv/    (images with boxes)
        output/yolo_labels_hsv/     (YOLO-format labels)
"""

import sys
import os
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
INPUT_DIR = OUTPUT / "yolo_input_hsv"
RESULT_DIR = OUTPUT / "yolo_results_hsv"
LABEL_DIR = OUTPUT / "yolo_labels_hsv"

MODEL_PATH = BASE.parent / "algae_guardian" / "data" / "fmpd_rdn_output" / \
             "yolo_results" / "v8l_upgrade" / "weights" / "best.pt"

CONF = 0.25
IMG_SIZE = 640


def main():
    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # ── Setup ──────────────────────────────────────
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    LABEL_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(INPUT_DIR.glob("*.jpg"))
    print(f"Model:  {MODEL_PATH}")
    print(f"Input:  {INPUT_DIR}/  ({len(images)} images)")
    print(f"Output: {RESULT_DIR}/")
    print(f"Device: {device}, conf={CONF}, imgsz={IMG_SIZE}")
    print()

    # ── Load model ─────────────────────────────────
    model = YOLO(str(MODEL_PATH))
    model.to(device)
    print(f"Classes: {model.names}\n")

    # ── Run inference ──────────────────────────────
    t0 = time.time()
    sleep_between = 0.15

    for i, img_path in enumerate(images):
        stem = img_path.stem

        results = model.predict(
            source=str(img_path),
            conf=CONF,
            imgsz=IMG_SIZE,
            device=device,
            verbose=False,
        )

        # Save detection visualization
        results[0].save(filename=str(RESULT_DIR / f"{stem}.jpg"))

        # Save YOLO-format labels
        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            h, w = results[0].orig_shape
            with open(LABEL_DIR / f"{stem}.txt", "w") as f:
                for b in boxes:
                    cls_id = int(b.cls.item())
                    conf = float(b.conf.item())
                    xyxy = b.xyxy[0].tolist()
                    # Convert to YOLO format: cls cx cy w h (normalized)
                    cx = ((xyxy[0] + xyxy[2]) / 2) / w
                    cy = ((xyxy[1] + xyxy[3]) / 2) / h
                    bw = (xyxy[2] - xyxy[0]) / w
                    bh = (xyxy[3] - xyxy[1]) / h
                    f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f} {conf:.6f}\n")

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (len(images) - i - 1)
            print(f"  {i+1}/{len(images)}  {elapsed:.0f}s elapsed, ETA {eta:.0f}s")

        time.sleep(sleep_between)
        if device == "cuda":
            torch.cuda.empty_cache()

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s ({elapsed/len(images):.1f}s/img)")

    # ── Summary ────────────────────────────────────
    result_imgs = list(RESULT_DIR.glob("*.jpg"))
    label_files = list(LABEL_DIR.glob("*.txt"))
    print(f"Results: {len(result_imgs)} images, {len(label_files)} label files")


if __name__ == "__main__":
    main()
