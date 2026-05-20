"""Lifewatch dataset preparation and processing pipeline.

Pipeline:
    1. Parse Lifewatch split files → YOLO format labels
    2. Organize images into train/val/test directories
    3. Run polarization simulation (RGB → I0/I45/I90/I135 .npz)
    4. Run RDN reconstruction (.npz → enhanced images)
    5. Create YOLO dataset config

Usage (on cloud server):
    /data/miniconda/envs/ican/bin/python -u prepare_lifewatch.py \
        --data-dir /data/datasets/lifewatch \
        --output-dir /data/lifewatch_yolo \
        --skip-polarization 0 \
        --split val,test \
        --img-size 640
"""

import argparse
import json
import sys
import os
import shutil
from pathlib import Path
from collections import defaultdict


def setup_paths():
    possible_roots = [
        Path(__file__).resolve().parent.parent,
        Path("/data/algae_guardian"),
    ]
    for root in possible_roots:
        if (root / "image_processing").exists() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
            return root
    return None


PROJECT_ROOT = setup_paths()


def parse_split_file(filepath: str) -> dict:
    """Parse Lifewatch split file (train.txt / val.txt / test.txt).

    Format: path\to\image.jpg class_index

    Returns {image_basename: class_index}
    """
    mapping = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            img_path, cls_idx = parts
            # Extract basename from path (handle both / and \)
            basename = img_path.replace("\\", "/").split("/")[-1]
            # Remove .jpg extension for key
            stem = basename.rsplit(".", 1)[0] if "." in basename else basename
            mapping[stem] = int(cls_idx)
    return mapping


def build_class_mapping(classes_file: str, lifewatch_root: str) -> dict:
    """Build {class_name: class_id} mapping."""
    with open(classes_file) as f:
        class_names = [line.strip() for line in f if line.strip()]
    return {name: idx for idx, name in enumerate(class_names)}, class_names


def find_image_by_stem(images_dir: str, stem: str) -> str | None:
    """Search all class directories for an image by its stem name."""
    # Check common extensions
    for ext in [".jpg", ".jpeg", ".png"]:
        # Walk all class dirs to find the file
        for cls_dir in os.listdir(images_dir):
            cls_path = os.path.join(images_dir, cls_dir)
            if not os.path.isdir(cls_path):
                continue
            img_path = os.path.join(cls_path, stem + ext)
            if os.path.exists(img_path):
                return img_path
    return None


def create_yolo_dataset(
    data_dir: str,
    output_dir: str,
    splits: list,
    class_names: list,
    img_size: int = 640,
):
    """Create YOLO-format dataset from Lifewatch splits.

    Directory structure:
        {output_dir}/
            {split}/
                images/
                labels/
            dataset.yaml
    """
    images_dir = os.path.join(data_dir, "images_all")
    dataset_files = os.path.join(data_dir, "dataset_files_equal")

    print(f"\n{'='*60}")
    print(f"  Creating YOLO dataset")
    print(f"{'='*60}")
    print(f"  Images dir: {images_dir}")
    print(f"  Splits: {splits}")
    print(f"  Output: {output_dir}")

    all_mappings = {}
    for split in splits:
        split_file = os.path.join(dataset_files, f"{split}.txt")
        if os.path.exists(split_file):
            print(f"\n  Parsing {split}.txt...")
            mapping = parse_split_file(split_file)
            all_mappings[split] = mapping
            print(f"    {len(mapping)} entries")
        else:
            print(f"  [WARN] {split}.txt not found, skipping")

    if not all_mappings:
        print("[ERROR] No split files found!")
        return

    # Build stem-to-fullpath index (one-time scan of all images)
    print(f"\n  Building image index across 95 class directories...")
    stem_to_path = {}
    for cls_dir in os.listdir(images_dir):
        cls_path = os.path.join(images_dir, cls_dir)
        if not os.path.isdir(cls_path):
            continue
        for fname in os.listdir(cls_path):
            stem = fname.rsplit(".", 1)[0] if "." in fname else fname
            stem_to_path[stem] = os.path.join(cls_path, fname)

    print(f"    {len(stem_to_path)} images indexed")

    # Create YOLO directories and copy images
    img_size_w, img_size_h = img_size, img_size  # square input

    for split, mapping in all_mappings.items():
        split_dir = os.path.join(output_dir, split)
        img_out_dir = os.path.join(split_dir, "images")
        lbl_out_dir = os.path.join(split_dir, "labels")
        os.makedirs(img_out_dir, exist_ok=True)
        os.makedirs(lbl_out_dir, exist_ok=True)

        copied = 0
        missing = 0
        for stem, cls_id in mapping.items():
            src = stem_to_path.get(stem)
            if src is None:
                missing += 1
                continue

            dst = os.path.join(img_out_dir, os.path.basename(src))
            if not os.path.exists(dst):
                shutil.copy2(src, dst)

            # Create YOLO label: class_id cx cy w h (full image = 0.5 0.5 1.0 1.0)
            label_path = os.path.join(lbl_out_dir, stem + ".txt")
            with open(label_path, "w") as f:
                f.write(f"{cls_id} 0.5 0.5 1.0 1.0\n")

            copied += 1

        print(f"    {split}/: {copied} copied, {missing} missing")

    # Create dataset.yaml
    nc = len(class_names)
    names_str = json.dumps(class_names)
    yaml_content = f"""# Lifewatch FlowCam Phytoplankton Dataset v2 (YOLO format)
# Auto-generated by prepare_lifewatch.py

path: {os.path.abspath(output_dir)}
train: train/images
val: val/images
test: test/images

nc: {nc}
names: {names_str}
"""
    yaml_path = os.path.join(output_dir, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    print(f"\n  dataset.yaml written (nc={nc})")
    print(f"  Output: {output_dir}/")
    for split in splits:
        if split in all_mappings:
            imgs = len(os.listdir(os.path.join(output_dir, split, "images")))
            lbls = len(os.listdir(os.path.join(output_dir, split, "labels")))
            print(f"    {split}/images/: {imgs}  labels/: {lbls}")


def run_polarization_simulation(
    input_dir: str,
    output_dir: str,
    strength: float = 1.0,
    preview: bool = False,
):
    """Run polarization simulation on RGB images."""
    from cloud_training.simulate_polarization import simulate_single_image, create_preview
    import numpy as np
    import cv2
    from tqdm import tqdm

    pol_dir = os.path.join(output_dir, "polarization")
    preview_dir = os.path.join(output_dir, "preview")
    os.makedirs(pol_dir, exist_ok=True)
    if preview:
        os.makedirs(preview_dir, exist_ok=True)

    img_files = []
    for ext in [".jpg", ".jpeg", ".png"]:
        img_files.extend(Path(input_dir).rglob(f"*{ext}"))
        img_files.extend(Path(input_dir).rglob(f"*{ext.upper()}"))
    img_files = sorted(set(img_files))

    print(f"\n  Polarization simulation: {len(img_files)} images")

    metadata = {}
    for img_path in tqdm(img_files, desc="  Pol sim"):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        try:
            channels = simulate_single_image(img_rgb, strength)
            stem = img_path.stem
            npz_path = os.path.join(pol_dir, f"{stem}.npz")
            np.savez_compressed(
                npz_path,
                I0=channels["I0"],
                I45=channels["I45"],
                I90=channels["I90"],
                I135=channels["I135"],
            )
            metadata[stem] = {
                "npz": f"polarization/{stem}.npz",
                "source": str(img_path),
            }
            if preview:
                prv = create_preview(channels)
                cv2.imwrite(
                    os.path.join(preview_dir, f"{stem}.jpg"),
                    cv2.cvtColor(prv, cv2.COLOR_RGB2BGR),
                )
        except Exception as e:
            print(f"  [ERR] {img_path.name}: {e}")

    # Save metadata
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Complete: {len(metadata)} .npz files in {pol_dir}/")


def run_rdn_reconstruction(
    input_dir: str,
    output_dir: str,
    model_path: str,
    img_size: int = 640,
    device: str = "cuda",
):
    """Run RDN reconstruction on .npz polarization files."""
    import numpy as np
    import cv2
    from tqdm import tqdm

    from ml.reconstructor import PolarizationReconstructor
    from image_processing.polarization import PolarizationProcessor
    from image_processing.enhancement import ImageEnhancer

    pol_dir = os.path.join(input_dir, "polarization")
    img_out_dir = os.path.join(output_dir, "images")
    preview_dir = os.path.join(output_dir, "YOLO_input_preview")
    os.makedirs(img_out_dir, exist_ok=True)
    os.makedirs(preview_dir, exist_ok=True)

    npz_files = sorted(Path(pol_dir).glob("*.npz"))
    print(f"\n  RDN reconstruction: {len(npz_files)} .npz files")

    # Load models
    reconstructor = PolarizationReconstructor(model_path=model_path, device=device)
    reconstructor.load_model()
    polarizer = PolarizationProcessor()
    enhancer = ImageEnhancer()

    for npz_path in tqdm(npz_files, desc="  RDN recon"):
        out_path = os.path.join(img_out_dir, f"{npz_path.stem}.jpg")
        if os.path.exists(out_path):
            continue
        try:
            data = np.load(npz_path)
            I0 = data["I0"].astype(np.float32)
            I45 = data["I45"].astype(np.float32)
            I90 = data["I90"].astype(np.float32)
            I135 = data["I135"].astype(np.float32)

            use_deep = reconstructor.is_available()
            recon_4ch = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=use_deep)

            I0_rec = recon_4ch[:, :, 0].astype(np.float32)
            I45_rec = recon_4ch[:, :, 1].astype(np.float32)
            I90_rec = recon_4ch[:, :, 2].astype(np.float32)
            I135_rec = recon_4ch[:, :, 3].astype(np.float32)
            S0 = I0_rec + I90_rec
            S1 = I0_rec - I90_rec
            S2 = I45_rec - I135_rec
            DoLP = np.sqrt(S1**2 + S2**2) / (S0 + 1e-10)
            DoLP = np.clip(DoLP, 0, 1)
            AoP = 0.5 * np.arctan2(S2, S1)

            enhanced = polarizer.polarization_enhancement_v2(S0, DoLP, AoP)
            corrected_raw = S0 * (1.0 - 0.5 * DoLP.astype(np.float32))
            corrected = ((corrected_raw - corrected_raw.min()) /
                         (corrected_raw.max() - corrected_raw.min() + 1e-10) * 255).astype(np.uint8)

            S0_norm = ((S0 - S0.min()) / (S0.max() - S0.min() + 1e-10) * 255).astype(np.uint8)
            recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
            final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)

            # Resize to YOLO input size (letterbox)
            h, w = final.shape[:2]
            scale = min(img_size / h, img_size / w)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(final, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            dw = img_size - new_w
            dh = img_size - new_h
            top, bottom = dh // 2, dh - dh // 2
            left, right = dw // 2, dw - dw // 2
            padded = cv2.copyMakeBorder(
                resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=(114, 114, 114),
            )

            cv2.imwrite(out_path, cv2.cvtColor(padded, cv2.COLOR_RGB2BGR))
            preview_path = os.path.join(preview_dir, f"{npz_path.stem}.jpg")
            cv2.imwrite(preview_path, cv2.cvtColor(padded, cv2.COLOR_RGB2BGR))

        except Exception as e:
            print(f"  [ERR] {npz_path.name}: {e}")

    n_out = len(os.listdir(img_out_dir))
    n_preview = len(os.listdir(preview_dir))
    print(f"  Complete: {n_out} images in {img_out_dir}/, {n_preview} previews in {preview_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Lifewatch pipeline")
    parser.add_argument("--data-dir", default="/data/datasets/lifewatch",
                        help="Lifewatch dataset root")
    parser.add_argument("--output-dir", default="/data/lifewatch_yolo",
                        help="Output directory")
    parser.add_argument("--model", default="/data/rdn_training/checkpoint/best.pth",
                        help="RDN model path")
    parser.add_argument("--img-size", type=int, default=640,
                        help="YOLO input size")
    parser.add_argument("--device", default="cuda",
                        help="Device: cuda or cpu")
    parser.add_argument("--splits", default="train,val,test",
                        help="Comma-separated split names")
    parser.add_argument("--skip-yolo-prep", action="store_true",
                        help="Skip YOLO dataset preparation")
    parser.add_argument("--skip-polarization", action="store_true",
                        help="Skip polarization simulation")
    parser.add_argument("--skip-rdn", action="store_true",
                        help="Skip RDN reconstruction")
    parser.add_argument("--polarization-strength", type=float, default=1.0)
    args = parser.parse_args()

    data_dir = args.data_dir
    dataset_files = os.path.join(data_dir, "dataset_files_equal")

    # Load class mapping
    classes_file = os.path.join(dataset_files, "classes.txt")
    if not os.path.exists(classes_file):
        print(f"[ERROR] classes.txt not found at {classes_file}")
        sys.exit(1)

    class_map, class_names = build_class_mapping(classes_file, data_dir)
    print(f"Loaded {len(class_names)} classes from {classes_file}")

    splits = [s.strip() for s in args.splits.split(",")]

    # Step 1: Create YOLO dataset
    if not args.skip_yolo_prep:
        create_yolo_dataset(
            data_dir=data_dir,
            output_dir=args.output_dir,
            splits=splits,
            class_names=class_names,
            img_size=args.img_size,
        )

    # Step 2-3: Polarization + RDN for each split
    for split in splits:
        split_img_dir = os.path.join(args.output_dir, split, "images")
        if not os.path.isdir(split_img_dir):
            print(f"\n[SKIP] {split}/images/ not found")
            continue

        # Polarization simulation
        pol_output_dir = os.path.join(args.output_dir, split, "polarized")
        if not args.skip_polarization:
            run_polarization_simulation(
                input_dir=split_img_dir,
                output_dir=pol_output_dir,
                strength=args.polarization_strength,
                preview=False,
            )

        # RDN reconstruction
        if not args.skip_rdn:
            rdn_output_dir = os.path.join(args.output_dir, split, "rdn_enhanced")
            run_rdn_reconstruction(
                input_dir=pol_output_dir,
                output_dir=rdn_output_dir,
                model_path=args.model,
                img_size=args.img_size,
                device=args.device,
            )

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Output: {args.output_dir}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
