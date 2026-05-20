"""Run YOLO detection on v2 pseudo-color images.
Input:  data/fmpd_rdn_output_v2/images/{stem}_{ts}.jpg
Output: data/fmpd_rdn_output_v2/yolo_results/{stem}_{ts}_detect.jpg
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
torch.serialization.add_safe_globals([torch.nn.Module])

from ultralytics import YOLO

V2_ROOT = Path(__file__).parent.parent / "data" / "rdn_output_v2"
IMAGE_DIR = V2_ROOT / "images"
OUTPUT_DIR = V2_ROOT / "yolo_results"
MODEL_PATH = Path(__file__).parent.parent / "data" / "yolo_results" / "training" / "weights" / "best.pt"

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    # Find latest v2 image batch
    image_files = sorted(IMAGE_DIR.glob("*.jpg"))
    if not image_files:
        print("No v2 images found!")
        return

    print(f"Model: {MODEL_PATH}")
    print(f"Images: {len(image_files)}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    model = YOLO(str(MODEL_PATH))
    model.to("cpu")
    print(f"Classes: {model.names}")

    summary = []
    for i, img_path in enumerate(image_files):
        # Extract original stem (before the timestamp)
        stem = img_path.stem.rsplit("_", 2)[0] if "_" in img_path.stem else img_path.stem
        print(f"[{i+1}/{len(image_files)}] {stem} ...", end=" ", flush=True)

        img_bgr = cv2.imread(str(img_path))
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        results = model.predict(
            source=img_rgb, conf=0.25, iou=0.45, imgsz=640,
            device="cpu", verbose=False,
        )

        det_counts = {}
        n_det = 0
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for cls_id in boxes.cls.cpu().numpy():
                name = model.names.get(int(cls_id), f"cls{int(cls_id)}")
                det_counts[name] = det_counts.get(name, 0) + 1
            n_det = len(boxes)

            # Save annotated
            annotated = results[0].plot()
            out_name = img_path.name.replace(".jpg", "_detect.jpg")
            cv2.imwrite(str(OUTPUT_DIR / out_name), annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            # No detections — just copy the image
            out_name = img_path.name.replace(".jpg", "_nodet.jpg")
            cv2.imwrite(str(OUTPUT_DIR / out_name), img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])

        print(f"{n_det} dets: {det_counts}")
        summary.append({"image": stem, "detections": det_counts, "total": n_det})

    # Summary
    total_dets = sum(s["total"] for s in summary)
    imgs_with_dets = sum(1 for s in summary if s["total"] > 0)
    print(f"\n{'=' * 60}")
    print(f"Total: {total_dets} detections across {imgs_with_dets}/{len(image_files)} images")

    # Class breakdown
    all_classes = {}
    for s in summary:
        for cls, cnt in s["detections"].items():
            all_classes[cls] = all_classes.get(cls, 0) + cnt
    for cls, cnt in sorted(all_classes.items(), key=lambda x: -x[1]):
        print(f"  {cls}: {cnt}")

    summary_path = OUTPUT_DIR / f"yolo_summary_{TIMESTAMP}.json"
    with open(summary_path, "w") as f:
        json.dump({"timestamp": TIMESTAMP, "model": str(MODEL_PATH),
                    "total_images": len(image_files), "total_detections": total_dets,
                    "class_counts": all_classes, "results": summary}, f, indent=2)
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
