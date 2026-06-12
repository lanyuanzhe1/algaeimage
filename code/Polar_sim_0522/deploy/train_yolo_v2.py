"""Train YOLOv8l with old hyperparameters (v8s-style) on HSV data.

Comparison experiment to isolate hyperparameter effect vs HSV method effect.
Key differences from baseline:
  - amp=False (was True — source of NaN)
  - lr0=0.0002 (was 0.001 — too aggressive for v8l)
  - hsv_s=0.7, hsv_v=0.4 (was 0.0 — missing regularization)
  - patience=20 (was 50 — shorter patience like old v8s)
"""

import argparse, time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="/data/lifewatch_hsv/yolo_results/v8l_hsv_stable")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch", type=int, default=24)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        torch.cuda.empty_cache()

    print(f"\n{'='*60}")
    print(f"v8l STABLE: amp=False lr0=0.0002 hsv_s=0.7 patience=20")
    print(f"Data: {args.data} | batch={args.batch}")
    print(f"{'='*60}\n")

    model = YOLO("/data/lifewatch_hsv/yolov8l.pt")
    t0 = time.time()

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        lr0=2e-4,
        lrf=1e-2,
        optimizer="AdamW",
        patience=20,
        device=device,
        project=str(Path(args.output).parent),
        name=Path(args.output).name,
        exist_ok=True,
        pretrained=True,
        seed=42,
        deterministic=True,
        amp=False,
        close_mosaic=10,
        warmup_epochs=3,
        warmup_momentum=0.8,
        weight_decay=5e-4,
        workers=args.workers,
        cache=False,
        plots=True,
        save=True,
        val=True,
        # Re-enable HSV augmentation (old v8s style)
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
        erasing=0.4,
        auto_augment="randaugment",
    )

    elapsed = time.time() - t0
    print(f"\nDone: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    print(f"Best epoch: {getattr(results, 'best_epoch', '?')}")
    print(f"Best fitness: {getattr(results, 'best_fitness', '?')}")


if __name__ == "__main__":
    main()
