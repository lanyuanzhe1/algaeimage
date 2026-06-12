"""Train YOLOv8l on LifeWatch HSV 95-class dataset.

Usage (on server):
    /data/miniconda/envs/torch/bin/python deploy/train_yolo.py \
        --data /data/lifewatch_hsv/processed/dataset.yaml \
        --output /data/lifewatch_hsv/yolo_results/v8l_hsv_95
"""

import argparse, time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="/data/lifewatch_hsv/yolo_results/v8l_hsv_95")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")
        torch.cuda.empty_cache()

    print(f"\n{'='*60}")
    print(f"YOLOv8l 95-class | {args.epochs}ep | batch={args.batch} | imgsz={args.imgsz}")
    print(f"Data: {args.data}")
    print(f"{'='*60}\n")

    model = YOLO("yolov8l.pt")
    t0 = time.time()

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        lr0=1e-3,
        lrf=1e-4,
        optimizer="AdamW",
        patience=50,
        device=device,
        project=str(Path(args.output).parent),
        name=Path(args.output).name,
        exist_ok=True,
        pretrained=True,
        seed=0,
        deterministic=True,
        amp=True,
        close_mosaic=10,
        warmup_epochs=5,
        warmup_momentum=0.8,
        weight_decay=5e-4,
        workers=args.workers,
        cache=False,
        plots=True,
        save=True,
        val=True,
        hsv_s=0.0,
        hsv_v=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
        erasing=0.4,
        auto_augment="randaugment",
    )

    elapsed = time.time() - t0
    print(f"\nTraining complete: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    print(f"Best epoch: {getattr(results, 'best_epoch', '?')}")
    print(f"Best fitness: {getattr(results, 'best_fitness', '?')}")


if __name__ == "__main__":
    main()
