"""Run YOLOv8s inference on the 293 FMPD images and export results."""
from ultralytics import YOLO
import os

model = YOLO("/data/fmpd_rdn_output/yolo_results/v8s_baseline/weights/best.pt")

results = model.predict(
    source="/data/fmpd_rdn_output/images/",
    save=True,
    save_txt=True,
    save_conf=True,
    project="/data/fmpd_rdn_output/yolo_results/",
    name="v8s_baseline_predict",
    exist_ok=True,
    imgsz=640,
    device=0,
    verbose=False,
)

print(f"DONE: {len(results)} images processed")

# Classification stats
names = model.names
counts = {}
for r in results:
    for c in r.boxes.cls:
        name = names[int(c)]
        counts[name] = counts.get(name, 0) + 1

print("Detections per class:")
for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {name}: {cnt}")

# Verify output
out_dir = "/data/fmpd_rdn_output/yolo_results/v8s_baseline_predict"
print(f"\nOutput dir: {out_dir}")
print("Labels:", len(os.listdir(f"{out_dir}/labels")) if os.path.exists(f"{out_dir}/labels") else 0)

# Print confusion-style summary per image
print("\nDone.")
