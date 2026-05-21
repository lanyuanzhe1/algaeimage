"""Train YOLOv8l on HSV polarization enhanced dataset.

Matches original training hyperparams (v8l_upgrade/args.yaml),
adjusted for RTX 4050 6GB (batch 8 vs 32).
"""

import time
from pathlib import Path
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent
DATASET_YAML = BASE / "output" / "yolo_training_hsv" / "dataset.yaml"
PROJECT_DIR = BASE / "output" / "yolo_training_hsv"
RUN_NAME = "v8l_hsv"

EPOCHS = 300
BATCH = 8
IMG_SIZE = 640
PATIENCE = 50
LR = 1e-3


def main():
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB)")
    print(f"Dataset: {DATASET_YAML}")
    print(f"Epochs: {EPOCHS}, Batch: {BATCH}, Patience: {PATIENCE}")
    print()

    # Clear CUDA cache before training
    if device == "cuda":
        torch.cuda.empty_cache()

    # Load pretrained YOLOv8l
    model = YOLO("yolov8l.pt")

    t0 = time.time()

    results = model.train(
        data=str(DATASET_YAML),
        epochs=EPOCHS,
        batch=BATCH,
        imgsz=IMG_SIZE,
        patience=PATIENCE,
        lr0=LR,
        lrf=0.0001,
        optimizer="AdamW",
        device=device,
        project=str(PROJECT_DIR),
        name=RUN_NAME,
        exist_ok=True,
        pretrained=True,
        seed=0,
        deterministic=True,
        amp=True,
        close_mosaic=10,
        cos_lr=False,
        warmup_epochs=5,
        warmup_momentum=0.8,
        weight_decay=0.0005,
        dropout=0.0,
        plots=True,
        save=True,
        val=True,
        workers=2,          # reduce to avoid CPU bottleneck
        cache=False,        # 6GB VRAM can't cache 234 images
        overlap_mask=True,
        hsv_h=0.015,
        hsv_s=0.0,          # HSV aug off (images already color-polarized)
        hsv_v=0.0,
        degrees=10,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.0,
        erasing=0.4,
        auto_augment="randaugment",
    )

    elapsed = time.time() - t0
    print(f"\nTraining done in {elapsed:.0f}s ({elapsed/3600:.1f}h)")

    # Print best results
    best_epoch = getattr(results, "best_epoch", "?")
    best_fitness = getattr(results, "best_fitness", "?")
    print(f"Best epoch: {best_epoch}, fitness: {best_fitness}")


if __name__ == "__main__":
    main()
