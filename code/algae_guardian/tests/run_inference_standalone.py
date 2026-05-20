"""Standalone inference: RGB → enhanced → YOLO detect → save outputs.

Matches the modified detection_service.py standard-RGB path (pseudo-polarization bypassed).
Processes real FMPD RDN output images + synthetic test samples.
Saves all outputs with "basename_timestamp" naming.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
from image_processing.enhancement import ImageEnhancer
from image_processing.quality import QualityAssessor
from ultralytics import YOLO

torch.serialization.add_safe_globals([torch.nn.Module])

# ── Config ──
PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = Path(__file__).parent / "samples"
FMPD_DIR = PROJECT_ROOT / "data" / "fmpd_rdn_output" / "images"
OUTPUT_DIR = Path(__file__).parent / "inference_output"
# Use the actual trained 5-class algae model
MODEL_PATH = PROJECT_ROOT / "data" / "yolo_results" / "training" / "weights" / "best.pt"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_image(img_bgr, stem, suffix):
    """Save BGR image, handle ascii-unfriendly stems."""
    safe_stem = stem.replace("/", "_").replace("\\", "_")
    fname = f"{safe_stem}_{TIMESTAMP}_{suffix}.png"
    fpath = OUTPUT_DIR / fname
    cv2.imwrite(str(fpath), img_bgr)
    return fpath


def process_image(img_rgb, stem, enhancer, quality, model, results_summary):
    """Process one RGB image through the fixed pipeline."""
    print(f"\n[{stem}]")
    print(f"  Shape: {img_rgb.shape}")

    # Step 2: Skip pseudo-polarization (the fix) → use original RGB directly
    aligned_image = img_rgb

    # Step 3: CLAHE + Color Correction
    enhanced_rgb = enhancer.enhance(aligned_image, dehaze=False,
                                    color_correct=True, clahe=True)

    # Step 4: Quality assessment
    q_report = quality.assess(enhanced_rgb)
    usable = quality.is_usable(q_report)
    print(f"  Q={q_report.quality_score:.4f}  contrast={q_report.contrast:.1f}  "
          f"sharpness={q_report.sharpness:.1f}  overall={q_report.overall_quality}  usable={usable}")
    if q_report.issues:
        print(f"  Issues: {q_report.issues}")

    # Step 5: YOLO detection
    yolo_results = model.predict(
        source=enhanced_rgb,
        conf=0.25,
        iou=0.45,
        imgsz=640,
        device="cpu",
        verbose=False,
    )

    det_counts = {}
    if yolo_results and len(yolo_results) > 0:
        boxes = yolo_results[0].boxes
        if boxes is not None and len(boxes) > 0:
            for cls_id in boxes.cls.cpu().numpy():
                name = model.names.get(int(cls_id), f"cls_{int(cls_id)}")
                det_counts[name] = det_counts.get(name, 0) + 1
    print(f"  Detections ({sum(det_counts.values())}): {det_counts}")

    # Save outputs
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    enhanced_bgr = cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2BGR)

    save_image(img_bgr, stem, "original")
    save_image(enhanced_bgr, stem, "enhanced")

    if yolo_results and len(yolo_results) > 0 and yolo_results[0].boxes is not None and len(yolo_results[0].boxes) > 0:
        annotated_bgr = yolo_results[0].plot()
        save_image(annotated_bgr, stem, "yolo_detect")
    else:
        save_image(enhanced_bgr, stem, "yolo_nodet")

    results_summary.append({
        "image": stem,
        "shape": list(img_rgb.shape),
        "quality_score": q_report.quality_score,
        "quality": q_report.overall_quality,
        "usable": usable,
        "contrast": q_report.contrast,
        "sharpness": q_report.sharpness,
        "brightness": q_report.brightness,
        "issues": q_report.issues,
        "detections": det_counts,
        "total_detections": sum(det_counts.values()),
    })


def main():
    enhancer = ImageEnhancer()
    quality = QualityAssessor()

    print(f"Loading YOLO model from: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    model.to("cpu")
    print(f"Model loaded. Classes: {model.names}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Timestamp: {TIMESTAMP}")

    results_summary = []

    # ── A. Process synthetic test samples ──
    print("\n" + "=" * 60)
    print("SYNTHETIC TEST SAMPLES")
    print("=" * 60)
    for fpath in sorted(SAMPLES_DIR.glob("*.png")):
        img_bgr = cv2.imread(str(fpath))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        process_image(img_rgb, fpath.stem, enhancer, quality, model, results_summary)

    # ── B. Process real FMPD RDN output images ──
    print("\n" + "=" * 60)
    print("FMPD RDN OUTPUT IMAGES")
    print("=" * 60)
    fmpd_files = sorted(FMPD_DIR.glob("*.jpg")) if FMPD_DIR.exists() else []
    for fpath in fmpd_files[:10]:  # First 10 for speed
        img_bgr = cv2.imread(str(fpath))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        process_image(img_rgb, fpath.stem, enhancer, quality, model, results_summary)

    # ── Save summary ──
    summary_path = OUTPUT_DIR / f"summary_{TIMESTAMP}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    print(f"\n{'=' * 60}")
    print(f"Summary: {summary_path}")
    print(f"Outputs: {OUTPUT_DIR}")
    print(f"Done.")


if __name__ == "__main__":
    main()
