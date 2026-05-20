"""YOLOv8s baseline training for FMPD dataset (5 classes)."""
from ultralytics import YOLO

model = YOLO("yolov8s.pt")
results = model.train(
    data="/data/fmpd_rdn_output/dataset.yaml",
    epochs=300,
    patience=50,
    batch=32,
    imgsz=640,
    device=0,
    workers=4,
    optimizer="AdamW",
    lr0=0.001,
    augment=True,
    mosaic=1.0,
    mixup=0.1,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=10,
    translate=0.1,
    scale=0.5,
    fliplr=0.5,
    cache=True,
    project="/data/fmpd_rdn_output/yolo_results",
    name="v8s_baseline",
    exist_ok=True,
    verbose=True,
)
