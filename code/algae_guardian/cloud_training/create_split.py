"""Create train/val split for FMPD dataset (80/20)."""
import json, random, shutil
from pathlib import Path

random.seed(42)
NPZ_DIR = Path(r"E:\code\codex\code\algae_guardian\data\fmpd_download\extracted\dataset\polarized\polarization")
OUTPUT_DIR = Path(r"E:\code\codex\code\algae_guardian\data\fmpd_rdn_output")
COCO_JSON = NPZ_DIR.parent.parent / "dataset" / "annotations.json"

# Get all stems
stems = sorted([f.stem for f in NPZ_DIR.glob("*.npz")])
random.shuffle(stems)
split_idx = int(len(stems) * 0.8)
train_stems = set(stems[:split_idx])
val_stems = set(stems[split_idx:])
print(f"Total: {len(stems)}, Train: {len(train_stems)}, Val: {len(val_stems)}")

# Move images/labels into train/ and val/ dirs
for split, stems_set in [("train", train_stems), ("val", val_stems)]:
    img_dir = OUTPUT_DIR / split / "images"
    lbl_dir = OUTPUT_DIR / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    for stem in stems_set:
        # Copy image
        src_img = OUTPUT_DIR / "images" / f"{stem}.jpg"
        dst_img = img_dir / f"{stem}.jpg"
        if src_img.exists():
            shutil.copy2(src_img, dst_img)
        # Copy label
        src_lbl = OUTPUT_DIR / "labels" / f"{stem}.txt"
        dst_lbl = lbl_dir / f"{stem}.txt"
        if src_lbl.exists():
            shutil.copy2(src_lbl, dst_lbl)

# Count labels per split per class
def count_labels(stems_set):
    counts = {}
    total = 0
    for stem in stems_set:
        lbl_path = OUTPUT_DIR / "labels" / f"{stem}.txt"
        if lbl_path.exists():
            with open(lbl_path) as f:
                for line in f:
                    cls = line.strip().split()[0]
                    counts[cls] = counts.get(cls, 0) + 1
                    total += 1
    return counts, total

from collections import Counter
train_counts, train_total = count_labels(train_stems)
val_counts, val_total = count_labels(val_stems)

class_names = ["Other-phytoplankton", "Non-phytoplankton", "Woronichinia", "Spiroides", "Dinobryon"]
print("\nTrain distribution:")
for i, name in enumerate(class_names):
    print(f"  {name}: {train_counts.get(str(i), 0)}")
print(f"  Total: {train_total}")
print("\nVal distribution:")
for i, name in enumerate(class_names):
    print(f"  {name}: {val_counts.get(str(i), 0)}")
print(f"  Total: {val_total}")

# Write dataset.yaml
yaml_content = f"""path: {OUTPUT_DIR.resolve()}
train: train/images
val: val/images
nc: 5
names: {json.dumps(class_names)}
"""
with open(OUTPUT_DIR / "dataset_split.yaml", "w") as f:
    f.write(yaml_content)
print(f"\ndataset_split.yaml written to {OUTPUT_DIR / 'dataset_split.yaml'}")
