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
    parser.add_argument("--lr", type=float, default=0.0002, help="Initial learning rate (reduced from 0.001 to prevent FP16 nan)")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument("--workers", type=int, default=8, help="Number of data loader workers")
    parser.add_argument("--cache", default="disk", help="Cache dataset ('disk', 'ram', or False)")
    parser.add_argument("--resume_best", action="store_true", help="Resume from best.pt check point with safety defenses")
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

    # 如果指定了 --resume_best，并且存在 best.pt 的健康权重，我们将从其上微调，并防御性关闭 amp 
    best_weights_path = f"{args.project}/{args.name}/weights/best.pt"
    if args.resume_best and os.path.exists(best_weights_path):
        print(f"🛡️ Defensively resuming training from healthy checkpoint: {best_weights_path}")
        print("🛡️ AMP is disabled (`amp=False`) to avoid gradients range overflow.")
        model = YOLO(best_weights_path)
        use_amp = False
    else:
        print(f"Loading base weights: {args.model}...")
        model = YOLO(args.model)
        use_amp = True

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
        amp=use_amp,                 # 基于安全防御考量，若使用 resume_best 则强制使用 FP32
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
