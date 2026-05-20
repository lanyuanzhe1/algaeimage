"""RDN reconstruction — standalone script with clear I/O folders.

Pipeline:
    .npz polarization files (I0/I45/I90/I135) → RDN reconstruction → enhanced images

Input structure (from simulate_polarization.py):
    {input_dir}/
        metadata.json
        polarization/           — .npz files with I0, I45, I90, I135 arrays
        preview/                (optional, from simulation step)

Output structure:
    {output_dir}/
        images/                 — RDN-enhanced 3-channel images (JPG), ready for YOLO
        dataset.yaml            — YOLO dataset config

Usage:
    python rdn_reconstruct.py \
        --input-dir /data/fmpd_polarized \
        --model /data/rdn_training/checkpoint/best.pth \
        --output-dir /data/fmpd_rdn_output \
        --img-size 640
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np
import cv2
from tqdm import tqdm


def setup_paths():
    """Ensure algae_guardian imports work from the cloud server."""
    possible_roots = [
        Path(__file__).resolve().parent.parent,
        Path("/data/algae_guardian"),
    ]
    for root in possible_roots:
        if (root / "ml").exists() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
            return root
    return None


PROJECT_ROOT = setup_paths()


def process_single_npz(
    npz_path: Path,
    reconstructor,
    polarizer,
    enhancer,
    img_size: int = 640,
) -> np.ndarray:
    """Process a single .npz polarization file through RDN reconstruction.

    Pipeline:
        .npz (I0/I45/I90/I135) → RDN reconstruction → I_enh enhancement → resize → output
    """
    data = np.load(npz_path)
    I0 = data["I0"].astype(np.float32)
    I45 = data["I45"].astype(np.float32)
    I90 = data["I90"].astype(np.float32)
    I135 = data["I135"].astype(np.float32)

    # ── RDN reconstruction (4-channel → 3-channel) ──
    use_deep = reconstructor.is_available()
    recon_3ch = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=use_deep)

    # ── I_enh polarization enhancement ──
    S0_recon = recon_3ch[:, :, 0].astype(np.float32)
    S1_recon = recon_3ch[:, :, 1].astype(np.float32) * 2 - 128
    S2_recon = recon_3ch[:, :, 2].astype(np.float32) * 2 - 128
    DoLP = np.sqrt(S1_recon**2 + S2_recon**2) / (S0_recon + 1e-10)
    AoP = 0.5 * np.arctan2(S2_recon, S1_recon)

    enhanced = polarizer.polarization_enhancement(S0_recon, DoLP, AoP)

    # ── Backscatter suppression ──
    corrected = polarizer.suppress_backscatter(S0_recon, DoLP)

    # ── Final image enhancement ──
    S0_norm = (
        (
            (S0_recon - S0_recon.min())
            / (S0_recon.max() - S0_recon.min() + 1e-10)
            * 255
        )
        .astype(np.uint8)
    )

    recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
    final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)

    # ── Resize to YOLO input size (letterbox) ──
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

    return padded


def create_yolo_dataset_yaml(output_dir: Path, num_classes: int, class_names: list):
    """Create dataset.yaml for YOLO training."""
    yaml_content = (
        f"# YOLO dataset config (auto-generated)\n"
        f"path: {output_dir.resolve()}\n"
        f"train: images\n"
        f"val: images\n\n"
        f"nc: {num_classes}\n"
        f"names: {json.dumps(class_names)}\n"
    )
    with open(output_dir / "dataset.yaml", "w") as f:
        f.write(yaml_content)
    print(f"  dataset.yaml created (nc={num_classes})")


def main():
    parser = argparse.ArgumentParser(description="RDN reconstruction from .npz polarization files")
    parser.add_argument("--input-dir", type=str, required=True,
                        help="Directory with polarization .npz files (from simulate_polarization.py)")
    parser.add_argument("--model", type=str,
                        default="/data/rdn_training/checkpoint/best.pth",
                        help="RDN model weights path")
    parser.add_argument("--output-dir", type=str, default="/data/fmpd_rdn_output",
                        help="Output directory for RDN-enhanced images")
    parser.add_argument("--img-size", type=int, default=640,
                        help="YOLO input size (default: 640)")
    parser.add_argument("--device", type=str, default="cuda",
                        help="Device: cuda or cpu")
    parser.add_argument("--coco-json", type=str, default="",
                        help="Path to COCO JSON (for YOLO label conversion)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    pol_dir = input_dir / "polarization"

    print("=" * 60)
    print("  RDN Reconstruction — .npz → Enhanced Images")
    print("=" * 60)
    print(f"  Input:    {pol_dir}/")
    print(f"  Model:    {args.model}")
    print(f"  Output:   {output_dir}/")
    print(f"  Device:   {args.device}")
    print("=" * 60)

    # ── Collect .npz files ──
    npz_files = sorted(pol_dir.glob("*.npz"))
    if not npz_files:
        print(f"[ERROR] No .npz files found in {pol_dir}")
        sys.exit(1)
    print(f"\n  Found {len(npz_files)} .npz files")

    # ── Convert COCO → YOLO labels (if provided) ──
    num_classes = 0
    class_names = []
    coco_json = args.coco_json
    if not coco_json:
        # Try common relative paths from input_dir
        for name in ["annotations.json", "_annotations.coco.json"]:
            p = input_dir / name
            if p.exists():
                coco_json = str(p)
                break

    if coco_json and Path(coco_json).exists():
        print(f"\n[1/4] Converting COCO annotations to YOLO format...")
        from cloud_training.batch_process_rdn import convert_coco_to_yolo
        num_imgs, num_anns, num_classes = convert_coco_to_yolo(
            coco_json, str(output_dir / "labels")
        )
        with open(coco_json) as f:
            coco_data = json.load(f)
        class_names = [cat["name"] for cat in coco_data["categories"]]
        print(f"      Images: {num_imgs}, Annotations: {num_anns}, Classes: {num_classes}")
    else:
        print(f"\n[1/4] No COCO JSON found — skipping label conversion")
        print(f"      YOLO training will be image-only (no labels)")

    # ── Load RDN model ──
    print(f"\n[2/4] Loading RDN model from {args.model}...")
    from ml.reconstructor import PolarizationReconstructor
    reconstructor = PolarizationReconstructor(model_path=args.model, device=args.device)
    loaded = reconstructor.load_model()
    print(f"      RDN loaded: {loaded}")

    # ── Load enhancer ──
    print(f"\n[3/4] Loading enhancement modules...")
    from image_processing.polarization import PolarizationProcessor
    from image_processing.enhancement import ImageEnhancer
    polarizer = PolarizationProcessor()
    enhancer = ImageEnhancer()

    # ── Process ──
    print(f"\n[4/4] Processing {len(npz_files)} files through RDN pipeline...")
    (output_dir / "images").mkdir(parents=True, exist_ok=True)

    for npz_path in tqdm(npz_files, desc="RDN reconstructing"):
        try:
            result = process_single_npz(
                npz_path, reconstructor, polarizer, enhancer,
                img_size=args.img_size,
            )

            # Save as JPG
            out_path = output_dir / "images" / f"{npz_path.stem}.jpg"
            cv2.imwrite(str(out_path), cv2.cvtColor(result, cv2.COLOR_RGB2BGR))

        except Exception as e:
            print(f"  [ERROR] {npz_path.name}: {e}")
            continue

    # ── Create dataset.yaml ──
    image_count = len(list((output_dir / "images").glob("*")))
    create_yolo_dataset_yaml(output_dir, num_classes or 1, class_names or ["algae"])

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE!")
    print(f"  Images:     {image_count} RDN-enhanced images")
    print(f"  Labels:     {len(list((output_dir / 'labels').glob('*.txt')))} YOLO labels"
          if (output_dir / "labels").exists() else "")
    print(f"  Config:     {output_dir / 'dataset.yaml'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
