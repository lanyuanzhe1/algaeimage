"""Generate HSV polarization RDN training data pairs from FMPD images.

Creates (noisy_input → clean_target) pairs for training polarization
reconstruction RDN with HSV-based polarization simulation.

Output: .mat files in noise/ and truth/ subdirectories.
"""
import sys
from pathlib import Path

# Add Polar_sim_0520 to path for hsv_polarization import
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Polar_sim_0520"))

import argparse
import numpy as np
import cv2
from scipy.io import savemat
from tqdm import tqdm

from hsv_polarization import hsv_to_polarization


def generate_pairs(input_dir: str, output_dir: str,
                   num_pairs: int = 5000,
                   eval_pairs: int = 200,
                   patch_size: int = 64,
                   noise_level: float = 0.05,
                   polar_strength_range: tuple = (0.5, 1.5)):
    """Generate (noisy input, clean target) pairs for HSV RDN training."""
    in_path = Path(input_dir)
    out_dir = Path(output_dir)

    for sub in ["noise", "truth", "eval_noise", "eval_truth"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    # Collect source images
    img_files = []
    for ext in ["*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg"]:
        img_files.extend(sorted(in_path.rglob(ext)))

    if not img_files:
        print(f"[ERROR] No images found in {input_dir}")
        return

    print(f"Found {len(img_files)} source images")

    # Pre-load all images
    images = []
    for f in tqdm(img_files, desc="Loading images"):
        img = cv2.imread(str(f))
        if img is None:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        if h < patch_size or w < patch_size:
            scale = max(patch_size / h, patch_size / w) * 1.2
            img = cv2.resize(img, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_LINEAR)
        images.append(img)

    if not images:
        print("[ERROR] No valid images loaded")
        return

    print(f"Loaded {len(images)} valid images")
    total_pairs = num_pairs + eval_pairs
    print(f"Generating {num_pairs} train + {eval_pairs} eval = {total_pairs} total pairs...")

    rng = np.random.default_rng(42)

    def save_pair(idx, patch, strength, noise_level, is_noisy, noise_dir, truth_dir):
        # Clean target
        ch_clean = hsv_to_polarization(patch, polarization_strength=strength,
                                       add_noise=False)
        target = np.zeros((patch_size, patch_size, 4), dtype=np.float32)
        target[:, :, 0] = ch_clean["I0"].astype(np.float32) / 255.0
        target[:, :, 1] = ch_clean["I45"].astype(np.float32) / 255.0
        target[:, :, 2] = ch_clean["I90"].astype(np.float32) / 255.0
        target[:, :, 3] = ch_clean["I135"].astype(np.float32) / 255.0

        if is_noisy:
            ch_noisy = hsv_to_polarization(patch, polarization_strength=strength,
                                           add_noise=True, noise_level=noise_level)
            input_data = np.zeros((patch_size, patch_size, 4), dtype=np.float32)
            input_data[:, :, 0] = ch_noisy["I0"].astype(np.float32) / 255.0
            input_data[:, :, 1] = ch_noisy["I45"].astype(np.float32) / 255.0
            input_data[:, :, 2] = ch_noisy["I90"].astype(np.float32) / 255.0
            input_data[:, :, 3] = ch_noisy["I135"].astype(np.float32) / 255.0
        else:
            input_data = target.copy()

        def normalize_minmax(data):
            mn = data.min(axis=(0, 1), keepdims=True)
            mx = data.max(axis=(0, 1), keepdims=True)
            return (data - mn) / (mx - mn + 1e-10)

        savemat(str(noise_dir / f"{idx:06d}.mat"),
                {"Norm_photon": normalize_minmax(input_data)})
        savemat(str(truth_dir / f"{idx:06d}.mat"),
                {"Norm_photon": normalize_minmax(target)})

    for i in tqdm(range(total_pairs), desc="Generating pairs"):
        img = images[rng.integers(len(images))]
        h, w = img.shape[:2]
        top = rng.integers(0, h - patch_size + 1)
        left = rng.integers(0, w - patch_size + 1)
        patch = img[top:top + patch_size, left:left + patch_size]
        strength = rng.uniform(*polar_strength_range)

        is_eval = i >= num_pairs
        if is_eval:
            save_pair(i - num_pairs, patch, strength, noise_level,
                      True, out_dir / "eval_noise", out_dir / "eval_truth")
        else:
            save_pair(i, patch, strength, noise_level,
                      True, out_dir / "noise", out_dir / "truth")

    print(f"\n[DONE] {num_pairs} train + {eval_pairs} eval pairs generated")
    print(f"  Train input:  {out_dir / 'noise'}/")
    print(f"  Train target: {out_dir / 'truth'}/")
    print(f"  Eval input:   {out_dir / 'eval_noise'}/")
    print(f"  Eval target:  {out_dir / 'eval_truth'}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate HSV polarization RDN training data")
    parser.add_argument("--input-dir", type=str, required=True,
                        help="Directory with source algae images (FMPD)")
    parser.add_argument("--output-dir", type=str, default="./data",
                        help="Output directory for .mat pairs")
    parser.add_argument("--num-pairs", type=int, default=5000)
    parser.add_argument("--eval-pairs", type=int, default=200)
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--noise-level", type=float, default=0.05)
    args = parser.parse_args()

    generate_pairs(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        num_pairs=args.num_pairs,
        eval_pairs=args.eval_pairs,
        patch_size=args.patch_size,
        noise_level=args.noise_level,
    )
