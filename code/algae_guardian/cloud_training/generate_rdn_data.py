"""Generate RDN training data pairs from standard algae datasets.

Creates (input → target) pairs for training the polarization reconstruction RDN:
    Input  (lr):  Simulated noisy DoFP polarization channels (I0, I45, I90, I135)
    Target (hr):  Clean reference (original or denoised RGB → polarization channels)

Output format: .mat files with 'Norm_photon' key, matching SPDRDN training format.

Usage:
    # From LifeWatch/FMPD raw images:
    python generate_rdn_training_data.py --input-dir ./datasets/lifewatch/images \\
        --output-dir ./data/rdn_training --num-pairs 10000

Output structure:
    rdn_training/
        noise/       ← input:  simulated DoFP with polarization modulation
           0001.mat, 0002.mat, ...
        truth/       ← target: clean reference
           0001.mat, 0002.mat, ...
"""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import numpy as np
import cv2
from scipy.io import savemat
from tqdm import tqdm

from image_processing.polarization_sim import simulate_polarization_channels


def generate_pairs(input_dir: str, output_dir: str,
                   num_pairs: int = 5000,
                   patch_size: int = 64,
                   noise_level: float = 0.05,
                   polar_strength_range: tuple = (0.5, 1.5)):
    """Generate (input, target) pairs for RDN training.

    For each pair:
        - Pick a random image from input_dir
        - Extract a random patch
        - Target: patch converted to 4-channel (I0, I45, I90, I135)
        - Input:  simulated polarization channels with added noise
    """
    in_path = Path(input_dir)
    out_noise = Path(output_dir) / "noise"
    out_truth = Path(output_dir) / "truth"
    out_noise.mkdir(parents=True, exist_ok=True)
    out_truth.mkdir(parents=True, exist_ok=True)

    # Collect all images
    img_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff"]:
        img_files.extend(sorted(in_path.rglob(ext)))

    if not img_files:
        print(f"[ERROR] No images found in {input_dir}")
        return

    print(f"Found {len(img_files)} source images")

    # Pre-load all images into memory for speed
    images = []
    for f in tqdm(img_files, desc="Loading images"):
        img = cv2.imread(str(f))
        if img is None:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        if h < patch_size or w < patch_size:
            # Resize small images
            scale = max(patch_size / h, patch_size / w) * 1.2
            new_h, new_w = int(h * scale), int(w * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        images.append(img)

    if not images:
        print("[ERROR] No valid images loaded")
        return

    print(f"Loaded {len(images)} valid images, generating {num_pairs} pairs...")

    np.random.seed(42)
    pair_idx = 0

    for i in tqdm(range(num_pairs), desc="Generating pairs"):
        # Pick random image and patch
        img = images[np.random.randint(len(images))]
        h, w = img.shape[:2]

        top = np.random.randint(0, h - patch_size + 1)
        left = np.random.randint(0, w - patch_size + 1)
        patch = img[top:top + patch_size, left:left + patch_size]

        # Random polarization strength for diversity
        strength = np.random.uniform(*polar_strength_range)

        # ── Target (clean) ──
        # Use clean simulation as target for all 4 polarization channels
        sim_clean = simulate_polarization_channels(patch, polarization_strength=strength,
                                                    add_shot_noise=False)
        target = np.zeros((patch_size, patch_size, 4), dtype=np.float32)
        target[:, :, 0] = sim_clean["I0"].astype(np.float32) / 255.0
        target[:, :, 1] = sim_clean["I45"].astype(np.float32) / 255.0
        target[:, :, 2] = sim_clean["I90"].astype(np.float32) / 255.0
        target[:, :, 3] = sim_clean["I135"].astype(np.float32) / 255.0

        # ── Input (noisy simulated DoFP) ──
        # Re-run with noise for the input side
        sim_noisy = simulate_polarization_channels(patch, polarization_strength=strength,
                                                    add_shot_noise=True, noise_level=noise_level)
        input_data = np.zeros((patch_size, patch_size, 4), dtype=np.float32)
        input_data[:, :, 0] = sim_noisy["I0"].astype(np.float32) / 255.0
        input_data[:, :, 1] = sim_noisy["I45"].astype(np.float32) / 255.0
        input_data[:, :, 2] = sim_noisy["I90"].astype(np.float32) / 255.0
        input_data[:, :, 3] = sim_noisy["I135"].astype(np.float32) / 255.0

        # Normalize both to [0, 1] with Norm_photon naming
        def normalize_minmax(data):
            data = data - np.min(data)
            data = data / (np.max(data) + 1e-10)
            return data

        # Save as .mat with 'Norm_photon' key (SPDRDN format)
        pair_idx += 1
        savemat(str(out_noise / f"{pair_idx:06d}.mat"),
                {"Norm_photon": normalize_minmax(input_data)})
        savemat(str(out_truth / f"{pair_idx:06d}.mat"),
                {"Norm_photon": normalize_minmax(target)})

        if pair_idx % 1000 == 0:
            print(f"  Generated {pair_idx}/{num_pairs} pairs")

    print(f"\n[DONE] {pair_idx} pairs generated")
    print(f"  Input:  {out_noise}/")
    print(f"  Target: {out_truth}/")
    print(f"  Now run SPDRDN's prepare.py to create train.h5/eval.h5")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate RDN training data pairs")
    parser.add_argument("--input-dir", type=str, required=True,
                        help="Directory with source algae images")
    parser.add_argument("--output-dir", type=str, default="./data/rdn_training",
                        help="Output directory for noise/ and truth/")
    parser.add_argument("--num-pairs", type=int, default=5000,
                        help="Number of training pairs to generate")
    parser.add_argument("--patch-size", type=int, default=64,
                        help="Patch size for training crops")
    parser.add_argument("--noise-level", type=float, default=0.05,
                        help="Noise level to add to simulated input")
    args = parser.parse_args()

    generate_pairs(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        num_pairs=args.num_pairs,
        patch_size=args.patch_size,
        noise_level=args.noise_level,
    )
