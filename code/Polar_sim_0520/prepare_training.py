"""Prepare HSV-enhanced dataset for YOLOv8l training.

Creates 80/20 train/val split from 293 HSV-enhanced images,
with YOLO-format labels from FMPD ground truth.
"""

import json
import shutil
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
TRAIN_DIR = OUTPUT / "yolo_training_hsv"
SRC_IMAGES = OUTPUT / "yolo_input_hsv"
SRC_LABELS = BASE.parent / "algae_guardian" / "data" / "fmpd_rdn_output" / "labels"

SEED = 42
TRAIN_RATIO = 0.8
CLASS_NAMES = ["Other-phytoplankton", "Non-phytoplankton",
               "Woronichinia", "Spiroides", "Dinobryon"]


def main():
    random.seed(SEED)

    # Collect all image-label pairs
    images = sorted(SRC_IMAGES.glob("*.jpg"))
    stems = [p.stem for p in images]
    print(f"Total images: {len(stems)}")

    # Verify labels exist
    valid_stems = []
    missing = 0
    for s in stems:
        if (SRC_LABELS / f"{s}.txt").exists():
            valid_stems.append(s)
        else:
            missing += 1
    if missing:
        print(f"  Warning: {missing} images missing labels")

    # Shuffle and split
    random.shuffle(valid_stems)
    n_train = int(len(valid_stems) * TRAIN_RATIO)
    train_stems = sorted(valid_stems[:n_train])
    val_stems = sorted(valid_stems[n_train:])

    print(f"Train: {len(train_stems)}, Val: {len(val_stems)}")

    # ── Create directories ──────────────────────────
    for split, stems_list in [("train", train_stems), ("val", val_stems)]:
        img_dir = TRAIN_DIR / split / "images"
        lbl_dir = TRAIN_DIR / split / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for stem in stems_list:
            # Copy image
            shutil.copy2(SRC_IMAGES / f"{stem}.jpg", img_dir / f"{stem}.jpg")
            # Copy label
            shutil.copy2(SRC_LABELS / f"{stem}.txt", lbl_dir / f"{stem}.txt")

        print(f"  {split}/: {len(stems_list)} images + labels")

    # ── dataset.yaml ────────────────────────────────
    yaml_content = f"""# HSV Polarization Enhanced YOLO Dataset
# Auto-generated for fair comparison training
path: {TRAIN_DIR.as_posix()}
train: train/images
val: val/images

nc: {len(CLASS_NAMES)}
names: {json.dumps(CLASS_NAMES)}
"""
    yaml_path = TRAIN_DIR / "dataset.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"\nDataset ready: {TRAIN_DIR}")
    print(f"  {yaml_path}")


if __name__ == "__main__":
    main()
