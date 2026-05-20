"""YOLOv8s polarization-enhanced training for LifeWatch FlowCam Dataset (95 classes).

Configuration:
    - Base Model: yolov8s.pt
    - Image Size: 320 px (Optimal for low-res FlowCam particles)
    - Optimization: AdamW, custom augmentations
"""

import os
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8s on LifeWatch Polarized Enhanced Dataset")
    parser.add_argument("--data", default="/data/lifewatch_yolo/dataset.yaml", help="Path to dataset.yaml")
    parser.add_argument("--model", default="yolov8s.pt", help="Pre-trained base model")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=128, help="Batch size (large batch fits easily in 16GB at imgsz=320)")
    parser.add_argument("--imgsz", type=int, default=320, help="Input image resolution")
    parser.add_argument("--device", default="0", help="GPU device ID")
    parser.add_argument("--name", default="lifewatch_v2_v8s_320", help="Experiment name")
    parser.add_argument("--project", default="/data/lifewatch_yolo/yolo_results", help="Project path for logs/weights")
    parser.add_argument("--lr", type=float, default=0.001, help="Initial learning rate")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument("--workers", type=int, default=8, help="Number of data loader workers")
    parser.add_argument("--cache", default="disk", help="Cache dataset ('disk', 'ram', or False)")
    args = parser.parse_args()

    print("=" * 60)
    print("  YOLOv8s Polarization-Enhanced Training initialized")
    print("=" * 60)
    print(f"  Data Path:    {args.data}")
    print(f"  Base Model:   {args.model}")
    print(f"  Resolution:   {args.imgsz}x{args.imgsz}")
    print(f"  Batch Size:   {args.batch}")
    print(f"  Epochs:       {args.epochs}")
    print(f"  Device:       GPU:{args.device}")
    print(f"  Saving to:    {args.project}/{args.name}/")
    print("=" * 60)

    # Automatically download/fetch pretrained base model
    print(f"Loading base weights: {args.model}...")
    model = YOLO(args.model)

    # Start training
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        patience=args.patience,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        workers=args.workers,
        optimizer="AdamW",
        lr0=args.lr,
        augment=True,
        mosaic=1.0,
        mixup=0.1,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        fliplr=0.5,
        cache=args.cache,
        project=args.project,
        name=args.name,
        exist_ok=True,
        verbose=True,
    )

    print(f"\nTraining complete. Best model weights saved at:")
    print(f"--> {args.project}/{args.name}/weights/best.pt")

if __name__ == "__main__":
    main()
