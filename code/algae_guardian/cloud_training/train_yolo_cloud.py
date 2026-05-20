"""YOLOv8 training script for cloud server.

Trains YOLOv8 on the RDN-processed FMPD dataset.

Usage:
    python train_yolo_cloud.py \
        --data /data/fmpd_rdn_output/dataset.yaml \
        --model /data/fmpd_rdn_output/yolov8n.pt \
        --epochs 100
"""

import argparse
import sys
from pathlib import Path

# Ensure ultralytics is available
try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 on RDN-processed FMPD")
    parser.add_argument("--data", type=str, default="/data/fmpd_rdn_output/dataset.yaml",
                        help="YOLO dataset config YAML")
    parser.add_argument("--model", type=str, default="yolov8n.pt",
                        help="Pretrained model (yolov8n.pt or path to existing weights)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="0",
                        help='GPU device (e.g., "0", "cpu")')
    parser.add_argument("--project", type=str, default="/data/fmpd_rdn_output/yolo_training",
                        help="Project directory for YOLO training outputs")
    parser.add_argument("--name", type=str, default="rdn_fmpd",
                        help="Experiment name")
    parser.add_argument("--patience", type=int, default=20,
                        help="Early stopping patience")
    args = parser.parse_args()

    print("=" * 60)
    print("  YOLOv8 Training on RDN-Processed FMPD")
    print("=" * 60)
    print(f"  Data config: {args.data}")
    print(f"  Pretrained:  {args.model}")
    print(f"  Epochs:      {args.epochs}")
    print(f"  Batch size:  {args.batch}")
    print(f"  Device:      {args.device}")
    print(f"  Image size:  {args.imgsz}")
    print("=" * 60)

    # Verify dataset config exists
    if not Path(args.data).exists():
        print(f"[ERROR] Dataset config not found: {args.data}")
        print("Run batch_process_rdn.py first to generate the dataset.")
        sys.exit(1)

    # Download pretrained model if needed
    if args.model == "yolov8n.pt" and not Path("yolov8n.pt").exists():
        print("\nDownloading YOLOv8n pretrained model...")
        from ultralytics import YOLO as YOLODownload
        model = YOLODownload("yolov8n.pt")
    else:
        model = YOLO(args.model)

    print("\nStarting training...")
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        lr0=args.lr,
        imgsz=args.imgsz,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=args.patience,
        augment=True,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        amp=True,
        verbose=True,
    )

    print(f"\nTraining complete! Results saved to {args.project}/{args.name}")
    print(f"Best model: {args.project}/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
