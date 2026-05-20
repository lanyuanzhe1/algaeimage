"""RDN batch processing for FMPD dataset on cloud server.

Pipeline for each image:
    RGB → simulate polarization (I0/I45/I90/I135) → RDN reconstruction → I_enh → save

Usage:
    # On cloud server:
    python batch_process_rdn.py \
        --data-dir /data/FMPD \
        --model /data/rdn_training/checkpoint/best.pth \
        --output /data/fmpd_rdn_output
"""

import argparse
import json
import sys
import os
from pathlib import Path
import numpy as np
import cv2
from tqdm import tqdm


def setup_paths():
    """Ensure we can import algae_guardian modules from cloud server."""
    # Check if we're running from within algae_guardian or standalone
    possible_roots = [
        Path(__file__).resolve().parent.parent,  # cloud_training/.. -> algae_guardian/
        Path("/data/algae_guardian"),
    ]
    for root in possible_roots:
        if (root / "ml").exists() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
            return root
    return None


PROJECT_ROOT = setup_paths()


def convert_coco_to_yolo(coco_json: str, output_dir: str):
    """Convert COCO JSON annotations to YOLO format .txt files.

    YOLO format: class_id cx cy w h  (normalized 0-1)
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(coco_json) as f:
        coco = json.load(f)

    # Build image id -> filename map
    img_map = {}
    for img_info in coco["images"]:
        img_id = img_info["id"]
        fname = Path(img_info["file_name"]).stem
        img_map[img_id] = {
            "file_name": fname,
            "width": img_info["width"],
            "height": img_info["height"],
        }

    # Build category id -> continuous class id map
    cat_map = {}
    for i, cat in enumerate(coco["categories"]):
        cat_map[cat["id"]] = i

    # Process annotations
    for ann in coco["annotations"]:
        img_id = ann["image_id"]
        img_info = img_map[img_id]
        w, h = img_info["width"], img_info["height"]

        # COCO bbox: [x, y, width, height] (top-left)
        bbox = ann["bbox"]
        x, y, bw, bh = bbox

        # Convert to YOLO format: class cx cy bw bh (normalized)
        cx = (x + bw / 2) / w
        cy = (y + bh / 2) / h
        bw_n = bw / w
        bh_n = bh / h

        class_id = cat_map[ann["category_id"]]

        label_path = out_dir / f"{img_info['file_name']}.txt"
        with open(label_path, "a") as f:
            f.write(f"{class_id} {cx:.6f} {cy:.6f} {bw_n:.6f} {bh_n:.6f}\n")

    classes_path = out_dir / "classes.txt"
    with open(classes_path, "w") as f:
        for cat in coco["categories"]:
            f.write(f"{cat['name']}\n")

    return len(coco["images"]), len(coco["annotations"]), len(coco["categories"])


def process_image(
    img_rgb: np.ndarray,
    reconstructor,
    polarizer,
    enhancer,
    img_size: int = 640,
) -> np.ndarray:
    """Process a single RGB image through the full pipeline.

    Pipeline:
        RGB → simulate polarization channels → RDN reconstruction
        → I_enh enhancement → resize → output
    """
    # Step 1: Simulate polarization
    from image_processing.polarization_sim import simulate_polarization_channels
    sim = simulate_polarization_channels(img_rgb, polarization_strength=1.0)
    I0 = sim["I0"].astype(np.float32)
    I45 = sim["I45"].astype(np.float32)
    I90 = sim["I90"].astype(np.float32)
    I135 = sim["I135"].astype(np.float32)

    # Step 2: RDN reconstruction (4-channel → 3-channel)
    use_deep = reconstructor.is_available()
    recon_3ch = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=use_deep)

    # Step 3: I_enh polarization enhancement
    S0_recon = recon_3ch[:, :, 0].astype(np.float32)
    S1_recon = recon_3ch[:, :, 1].astype(np.float32) * 2 - 128
    S2_recon = recon_3ch[:, :, 2].astype(np.float32) * 2 - 128
    DoLP = np.sqrt(S1_recon**2 + S2_recon**2) / (S0_recon + 1e-10)
    AoP = 0.5 * np.arctan2(S2_recon, S1_recon)

    enhanced = polarizer.polarization_enhancement(S0_recon, DoLP, AoP)

    # Step 4: Final image enhancement
    S0_norm = ((S0_recon - S0_recon.min()) / (S0_recon.max() - S0_recon.min() + 1e-10) * 255).astype(np.uint8)
    corrected = polarizer.suppress_backscatter(S0_recon, DoLP)

    recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
    final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)

    # Step 5: Resize to YOLO input size
    h, w = final.shape[:2]
    scale = min(img_size / h, img_size / w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(final, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Letterbox padding
    dw = img_size - new_w
    dh = img_size - new_h
    top, bottom = dh // 2, dh - dh // 2
    left, right = dw // 2, dw - dw // 2
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                cv2.BORDER_CONSTANT, value=(114, 114, 114))

    # Return both padded image and scale/padding info for label adjustment
    meta = {"scale": scale, "pad": (left, top, dw, dh)}
    return padded, meta


def adjust_yolo_labels(label_path: str, meta: dict, img_size: int = 640):
    """Adjust YOLO labels after letterbox padding."""
    if not os.path.exists(label_path):
        return

    scale = meta["scale"]
    pad_left, pad_top, dw, dh = meta["pad"]

    lines = []
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls_id = parts[0]
            cx, cy, bw, bh = map(float, parts[1:])

            # Original image dimensions (as fraction of padded)
            orig_w = 1.0 - dw / img_size
            orig_h = 1.0 - dh / img_size

            # Adjust from padded coordinates to original image coords
            cx_img = (cx * img_size - pad_left) / (orig_w * img_size)
            cy_img = (cy * img_size - pad_top) / (orig_h * img_size)
            bw_img = bw / scale / orig_w if orig_w > 0 else bw
            bh_img = bh / scale / orig_h if orig_h > 0 else bh

            # Clamp
            cx_img = max(0, min(1, cx_img))
            cy_img = max(0, min(1, cy_img))
            bw_img = max(0, min(1, bw_img))
            bh_img = max(0, min(1, bh_img))

            lines.append(f"{cls_id} {cx_img:.6f} {cy_img:.6f} {bw_img:.6f} {bh_img:.6f}")

    with open(label_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Batch RDN processing for FMPD dataset")
    parser.add_argument("--data-dir", type=str, default="/data/FMPD",
                        help="FMPD dataset root (with images/ and annotations.json)")
    parser.add_argument("--model", type=str,
                        default="/data/rdn_training/checkpoint/best.pth",
                        help="RDN model weights path")
    parser.add_argument("--output", type=str, default="/data/fmpd_rdn_output",
                        help="Output directory for processed images")
    parser.add_argument("--img-size", type=int, default=640,
                        help="YOLO input size")
    parser.add_argument("--device", type=str, default="cuda",
                        help="Device: cuda or cpu")
    parser.add_argument("--coco-json", type=str, default="",
                        help="Path to COCO JSON (if not in --data-dir)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output)

    print("=" * 60)
    print("  RDN Batch Processing for FMPD Dataset")
    print("=" * 60)

    # ── Locate COCO JSON ──
    coco_json = args.coco_json or str(data_dir / "annotations.json")
    if not Path(coco_json).exists():
        # Try common names
        for name in ["annotations.json", "_annotations.coco.json", "coco.json"]:
            p = data_dir / name
            if p.exists():
                coco_json = str(p)
                break
            # Also search in subdirectories
            for f in data_dir.rglob(name):
                coco_json = str(f)
                break

    print(f"\n[1/5] Converting COCO annotations to YOLO format...")
    if Path(coco_json).exists():
        num_imgs, num_anns, num_cls = convert_coco_to_yolo(
            coco_json, str(output_dir / "labels")
        )
        print(f"      Images: {num_imgs}, Annotations: {num_anns}, Classes: {num_cls}")
    else:
        print(f"      [WARN] COCO JSON not found in {data_dir}")
        print(f"      Continuing with images only...")

    # ── Load models ──
    print(f"\n[2/5] Loading RDN model from {args.model}...")
    from ml.reconstructor import PolarizationReconstructor
    reconstructor = PolarizationReconstructor(model_path=args.model, device=args.device)
    loaded = reconstructor.load_model()
    print(f"      RDN model loaded: {loaded}")

    print(f"\n[3/5] Loading polarization processor and enhancer...")
    from image_processing.polarization import PolarizationProcessor
    from image_processing.enhancement import ImageEnhancer
    polarizer = PolarizationProcessor()
    enhancer = ImageEnhancer()

    # ── Collect images ──
    print(f"\n[4/5] Scanning for images in {data_dir}...")
    img_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff"]:
        img_files.extend(sorted(data_dir.rglob(ext)))

    # Exclude already processed
    processed_dir = output_dir / "images"
    processed_names = {p.stem for p in processed_dir.glob("*")} if processed_dir.exists() else set()
    img_files = [f for f in img_files if f.stem not in processed_names]

    if not img_files:
        print("      No new images found!")
        return

    print(f"      Found {len(img_files)} images to process")

    # ── Process ──
    print(f"\n[5/5] Processing images through RDN pipeline...")
    (output_dir / "images").mkdir(parents=True, exist_ok=True)

    for img_path in tqdm(img_files, desc="RDN processing"):
        # Read image
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"      [SKIP] Cannot read: {img_path}")
            continue
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        try:
            # Process through pipeline
            result_padded, meta = process_image(
                img_rgb, reconstructor, polarizer, enhancer,
                img_size=args.img_size,
            )

            # Save processed image
            out_path = output_dir / "images" / f"{img_path.stem}.jpg"
            cv2.imwrite(str(out_path), cv2.cvtColor(result_padded, cv2.COLOR_RGB2BGR))

            # Adjust labels for letterbox padding
            label_path = output_dir / "labels" / f"{img_path.stem}.txt"
            if label_path.exists():
                adjust_yolo_labels(str(label_path), meta, args.img_size)

        except Exception as e:
            print(f"      [ERROR] {img_path.name}: {e}")
            continue

    # ── Create YOLO dataset config ──
    print(f"\nCreating YOLO dataset config...")
    yaml_content = f"""
# YOLO dataset config (auto-generated)
path: {output_dir.resolve()}
train: images
val: images

nc: {num_cls if Path(coco_json).exists() else 1}
names: {json.dumps([cat['name'] for cat in json.load(open(coco_json))['categories']]) if Path(coco_json).exists() else "['algae']"}
"""
    with open(output_dir / "dataset.yaml", "w") as f:
        f.write(yaml_content)

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE!")
    print(f"  Output: {output_dir}/")
    print(f"    images/   - {len(list((output_dir / 'images').glob('*')))} RDN-processed images")
    print(f"    labels/   - YOLO-format label files")
    print(f"    dataset.yaml - YOLO training config")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
