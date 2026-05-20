"""YOLOv8 training for LifeWatch FlowCam Phytoplankton Dataset v2.

95 classes, 337k images (302k train, 13k val, 21k test).

Usage:
    python train_lifewatch_yolo.py \
        --data /data/lifewatch_yolo/dataset.yaml \
        --model yolov8n.pt \
        --epochs 100 \
        --batch 64 \
        --name lifewatch_v8n
"""

import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="/data/lifewatch_yolo/dataset.yaml")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--device", default="0")
    parser.add_argument("--name", default="lifewatch_v8n")
    parser.add_argument("--project", default="/data/lifewatch_yolo/yolo_results")
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cache", default="disk")
    args = parser.parse_args()

    print(f"Training YOLO on LifeWatch dataset")
    print(f"  Data: {args.data}")
    print(f"  Model: {args.model}")
    print(f"  Epochs: {args.epochs}, Batch: {args.batch}, ImgSz: {args.imgsz}")
    print(f"  Device: {args.device}")

    model = YOLO(args.model)

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

    print(f"\nTraining complete. Best model: {args.project}/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
