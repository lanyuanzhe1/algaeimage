"""Polarization simulation — standalone script with clear I/O folders.

Pipeline:
    Input RGB images → simulate I0/I45/I90/I135 → save as .npz for RDN

Output structure:
    {output_dir}/
        metadata.json       — mapping from original filenames to output files
        polarization/       — .npz files, each containing arrays [I0, I45, I90, I135]
        preview/            — optional RGB previews of simulated channels

Usage:
    python simulate_polarization.py \
        --input-dir /data/FMPD/dataset \
        --output-dir /data/fmpd_polarized \
        --polarization-strength 1.0
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
        if (root / "image_processing").exists() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
            return root
    return None


PROJECT_ROOT = setup_paths()


def simulate_single_image(img_rgb: np.ndarray, strength: float = 1.0) -> dict:
    """Simulate 4 polarization channels from an RGB image.

    Returns dict with I0, I45, I90, I135 as np.ndarray (H, W), float32.
    """
    from image_processing.polarization_sim import simulate_polarization_channels

    sim = simulate_polarization_channels(img_rgb, polarization_strength=strength)
    I0 = sim["I0"].astype(np.float32)
    I45 = sim["I45"].astype(np.float32)
    I90 = sim["I90"].astype(np.float32)
    # I135 is interpolated from I0 and I90 per the DoFP pattern
    I135 = sim["I135"].astype(np.float32)

    return {"I0": I0, "I45": I45, "I90": I90, "I135": I135}


def create_previews(channels: dict) -> dict:
    """Create 3 preview images from 4 polarization channels.

    Returns dict with:
        "stokes": S0 | S1 | S2 side-by-side grayscale comparison
        "aop":    AoP color-coded via HSV (hue=angle, saturation=DoLP)
        "dolp":   DoLP grayscale
    """
    from image_processing.polarization import PolarizationProcessor

    pp = PolarizationProcessor()
    stokes = pp.reconstruct_stokes(channels["I0"], channels["I45"],
                                    channels["I90"], channels["I135"])

    S0 = stokes["S0"].astype(np.float32)
    S1 = stokes["S1"].astype(np.float32)
    S2 = stokes["S2"].astype(np.float32)
    DoLP = stokes["DoLP"].astype(np.float32)
    AoP = stokes["AoP"].astype(np.float32)

    def normalize(x):
        x_min, x_max = x.min(), x.max()
        if x_max - x_min < 1e-10:
            return np.zeros_like(x, dtype=np.uint8)
        return ((x - x_min) / (x_max - x_min) * 255).astype(np.uint8)

    def normalize_signed(x):
        """Normalize signed data: 0 → gray128, preserving sign."""
        max_abs = np.max(np.abs(x)) + 1e-10
        return np.clip(x / max_abs * 127 + 127, 0, 255).astype(np.uint8)

    # ── Image 1: S0 | S1 | S2 side-by-side ──
    s0_panel = np.stack([normalize(S0)] * 3, axis=-1)
    s1_panel = np.stack([normalize_signed(S1)] * 3, axis=-1)
    s2_panel = np.stack([normalize_signed(S2)] * 3, axis=-1)

    h, w = s0_panel.shape[:2]
    # Add dividing lines (3px white gap)
    divider = np.full((h, 3, 3), 255, dtype=np.uint8)
    stokes_img = np.concatenate([s0_panel, divider, s1_panel, divider, s2_panel], axis=1)

    # Labels on each panel
    font = cv2.FONT_HERSHEY_SIMPLEX
    def add_label(img, text, pos=(8, 28)):
        cv2.putText(img, text, pos, font, 0.8, (0, 0, 0), 4)
        cv2.putText(img, text, pos, font, 0.8, (255, 255, 255), 2)

    add_label(stokes_img, "S0", (8, 28))
    add_label(stokes_img, "S1", (w + 11, 28))
    add_label(stokes_img, "S2", (2 * w + 14, 28))

    # ── Image 2: AoP color-coded via HSV ──
    aop_hue = ((AoP + np.pi / 2) / np.pi * 180).astype(np.uint8)
    aop_sat = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
    aop_val = normalize(S0)
    aop_hsv = cv2.merge([aop_hue, aop_sat, aop_val])
    aop_img = cv2.cvtColor(aop_hsv, cv2.COLOR_HSV2RGB)
    add_label(aop_img, "AoP")

    # ── Image 3: DoLP grayscale ──
    dolp_norm = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
    dolp_img = np.stack([dolp_norm] * 3, axis=-1)
    add_label(dolp_img, "DoLP")

    return {"stokes": stokes_img, "aop": aop_img, "dolp": dolp_img}


def create_preview(channels: dict) -> np.ndarray:
    """Create a single stitched preview image from polarization channels."""
    previews = create_previews(channels)
    stokes = previews["stokes"]
    aop = previews["aop"]
    dolp = previews["dolp"]
    
    h, w = aop.shape[:2]
    divider = np.full((h, 3, 3), 255, dtype=np.uint8)
    preview_stitched = np.concatenate([stokes, divider, aop, divider, dolp], axis=1)
    return preview_stitched


def main():
    parser = argparse.ArgumentParser(description="RGB → Polarization simulation")
    parser.add_argument("--input-dir", type=str, required=True,
                        help="Directory with input RGB images")
    parser.add_argument("--output-dir", type=str, required=True,
                        help="Output directory for polarization data")
    parser.add_argument("--polarization-strength", type=float, default=1.0,
                        help="Polarization effect strength (default: 1.0)")
    parser.add_argument("--preview", action="store_true",
                        help="Generate RGB preview images")
    parser.add_argument("--extensions", type=str, default=".jpg,.jpeg,.png,.tif,.tiff",
                        help="Comma-separated list of image extensions to process")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    pol_dir = output_dir / "polarization"
    preview_dir = output_dir / "preview"

    print("=" * 60)
    print("  Polarization Simulation — RGB → I0/I45/I90/I135")
    print("=" * 60)
    print(f"  Input:         {input_dir}")
    print(f"  Output:        {output_dir}")
    print(f"  Strength:      {args.polarization_strength}")
    print(f"  Preview:       {'yes' if args.preview else 'no'}")
    print("=" * 60)

    # ── Collect images ──
    extensions = [f".{e.strip().lstrip('.')}" for e in args.extensions.split(",")]
    img_files = []
    for ext in extensions:
        img_files.extend(sorted(input_dir.rglob(f"*{ext}")))
    # Also match case variants
    for ext in extensions:
        img_files.extend(sorted(input_dir.rglob(f"*{ext.upper()}")))

    if not img_files:
        print(f"[ERROR] No images found in {input_dir}")
        sys.exit(1)

    # Deduplicate
    seen = set()
    unique = []
    for f in img_files:
        if f.suffix.lower() in extensions and f not in seen:
            seen.add(f)
            unique.append(f)
    img_files = unique

    print(f"\n  Found {len(img_files)} images to process\n")

    # ── Create output dirs ──
    pol_dir.mkdir(parents=True, exist_ok=True)
    if args.preview:
        preview_dir.mkdir(parents=True, exist_ok=True)

    # ── Process ──
    metadata = {}
    for img_path in tqdm(img_files, desc="Simulating polarization"):
        # Read image
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  [SKIP] Cannot read: {img_path}")
            continue
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        try:
            channels = simulate_single_image(img_rgb, args.polarization_strength)

            # Save as .npz — 4 arrays ready for RDN input
            stem = img_path.stem
            npz_path = pol_dir / f"{stem}.npz"
            np.savez_compressed(npz_path,
                                I0=channels["I0"],
                                I45=channels["I45"],
                                I90=channels["I90"],
                                I135=channels["I135"])

            # Optionally save previews
            if args.preview:
                previews = create_previews(channels)
                for key, img in previews.items():
                    preview_path = preview_dir / f"{stem}_{key}.jpg"
                    cv2.imwrite(str(preview_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

            metadata[stem] = {
                "original": str(img_path.relative_to(input_dir)),
                "polarization_npz": str(npz_path.relative_to(output_dir)),
                "shape": list(channels["I0"].shape),
            }

        except Exception as e:
            print(f"  [ERROR] {img_path.name}: {e}")
            continue

    # ── Save metadata ──
    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE!")
    print(f"  Processed: {len(metadata)} / {len(img_files)} images")
    print(f"  Output:    {pol_dir}/  ({len(list(pol_dir.glob('*.npz')))} .npz files)")
    print(f"  Metadata:  {meta_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
