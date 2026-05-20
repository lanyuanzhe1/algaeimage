"""Enhance polarization previews for better visual distinction.

Reads .npz files (I0/I45/I90/I135), computes Stokes parameters,
and generates 3 enhanced preview images per sample:
  1. S0|S1|S2 — side-by-side grayscale with CLAHE per panel
  2. AoP     — HSV color-coded with boosted saturation + CLAHE on value
  3. DoLP    — CLAHE + gamma correction

Usage:
    python enhance_polarization_preview.py \
        --npz-dir /path/to/polarization/ \
        --output-dir /path/to/enhanced_previews/
"""
import argparse
import sys
from pathlib import Path
import numpy as np
import cv2


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


def _clahe(gray: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    """Apply CLAHE to a uint8 grayscale image."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    return clahe.apply(gray)


def _add_label(img: np.ndarray, text: str, pos=(10, 30)):
    """Draw label with dark shadow for readability."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, pos, font, 0.8, (0, 0, 0), 4)
    cv2.putText(img, text, pos, font, 0.8, (255, 255, 255), 2)


def enhance_stokes(S0: np.ndarray, S1: np.ndarray, S2: np.ndarray) -> np.ndarray:
    """S0 | S1 | S2 side-by-side, CLAHE per panel.

    S0: min-max normalize → CLAHE
    S1/S2: signed normalize (0→gray128) → CLAHE to spread subtle differences
    """
    def _norm_uint8(x):
        x_min, x_max = x.min(), x.max()
        if x_max - x_min < 1e-10:
            return np.zeros_like(x, dtype=np.uint8)
        return ((x - x_min) / (x_max - x_min) * 255).astype(np.uint8)

    def _norm_signed(x):
        max_abs = np.max(np.abs(x)) + 1e-10
        return np.clip(x / max_abs * 127 + 127, 0, 255).astype(np.uint8)

    s0_panel = np.stack([_clahe(_norm_uint8(S0))] * 3, axis=-1)
    s1_panel = np.stack([_clahe(_norm_signed(S1))] * 3, axis=-1)
    s2_panel = np.stack([_clahe(_norm_signed(S2))] * 3, axis=-1)

    h, w = s0_panel.shape[:2]
    divider = np.full((h, 3, 3), 255, dtype=np.uint8)
    img = np.concatenate([s0_panel, divider, s1_panel, divider, s2_panel], axis=1)

    _add_label(img, "S0", (8, 28))
    _add_label(img, "S1", (w + 11, 28))
    _add_label(img, "S2", (2 * w + 14, 28))
    return img


def enhance_aop(AoP: np.ndarray, DoLP: np.ndarray, S0: np.ndarray) -> np.ndarray:
    """AoP color-coded via HSV with boosted saturation + CLAHE on value.

    - Hue = AoP angle [-π/2, π/2] → [0, 180]
    - Saturation = max(DoLP * 255, 100) — floor at ~0.4 so angle visible everywhere
    - Value = CLAHE(S0_norm) — structural detail
    """
    def _norm_uint8(x):
        x_min, x_max = x.min(), x.max()
        if x_max - x_min < 1e-10:
            return np.zeros_like(x, dtype=np.uint8)
        return ((x - x_min) / (x_max - x_min) * 255).astype(np.uint8)

    aop_hue = ((AoP + np.pi / 2) / np.pi * 180).astype(np.uint8)
    aop_sat = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
    aop_sat = np.maximum(aop_sat, 100).astype(np.uint8)
    aop_val = _clahe(_norm_uint8(S0))

    aop_hsv = cv2.merge([aop_hue, aop_sat, aop_val])
    img = cv2.cvtColor(aop_hsv, cv2.COLOR_HSV2RGB)
    _add_label(img, "AoP")
    return img


def enhance_dolp(DoLP: np.ndarray) -> np.ndarray:
    """DoLP grayscale with CLAHE + gamma correction.

    Gamma < 1 brightens mid/low-tones so subtle polarization differences pop.
    """
    norm = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
    enhanced = _clahe(norm)
    # Gamma < 1 to lift dark/mid regions
    enhanced = (np.power(enhanced / 255.0, 0.7) * 255).astype(np.uint8)
    img = np.stack([enhanced] * 3, axis=-1)
    _add_label(img, "DoLP")
    return img


def main():
    parser = argparse.ArgumentParser(description="Enhance polarization previews")
    parser.add_argument("--npz-dir", type=str, required=True,
                        help="Directory with .npz files (I0/I45/I90/I135)")
    parser.add_argument("--output-dir", type=str, required=True,
                        help="Output directory for enhanced JPG previews")
    args = parser.parse_args()

    npz_dir = Path(args.npz_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    npz_files = sorted(npz_dir.glob("*.npz"))
    if not npz_files:
        print(f"[ERROR] No .npz files in {npz_dir}")
        sys.exit(1)

    print(f"Processing {len(npz_files)} files ...")

    for npz_path in npz_files:
        data = np.load(npz_path)
        I0 = data["I0"].astype(np.float32)
        I45 = data["I45"].astype(np.float32)
        I90 = data["I90"].astype(np.float32)
        I135 = data["I135"].astype(np.float32)

        # Stokes
        S0 = I0 + I90
        S1 = I0 - I90
        S2 = I45 - I135
        denom = S0 + 1e-10
        DoLP = np.sqrt(S1 ** 2 + S2 ** 2) / denom
        DoLP = np.clip(DoLP, 0, 1)
        AoP = 0.5 * np.arctan2(S2, S1)

        stem = npz_path.stem

        stokes_img = enhance_stokes(S0, S1, S2)
        aop_img = enhance_aop(AoP, DoLP, S0)
        dolp_img = enhance_dolp(DoLP)

        cv2.imwrite(str(out_dir / f"{stem}_stokes.jpg"), cv2.cvtColor(stokes_img, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(out_dir / f"{stem}_aop.jpg"), cv2.cvtColor(aop_img, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(out_dir / f"{stem}_dolp.jpg"), cv2.cvtColor(dolp_img, cv2.COLOR_RGB2BGR))

    print(f"[DONE] {len(npz_files)} files → {out_dir}/")


if __name__ == "__main__":
    main()
