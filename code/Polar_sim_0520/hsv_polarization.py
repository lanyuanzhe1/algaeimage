"""HSV-based polarization simulation (Yan et al., Photonics 2024).

Maps RGB → HSV color space, then:
    H (Hue)        → AoP (Angle of Polarization)    [0, π)
    S (Saturation) → DoLP (Degree of Linear Polarization) [0, 1]
    V (Value)      → S₀ (Total Intensity)           [0, 1]

Then uses the Stokes polarimetric model to compute 4-channel output:
    I(θ) = ½ S₀ × (1 + DoLP × cos(2(θ − AoP)))

Reference:
    Yan et al., "Training a Dataset Simulated Using RGB Images for an
    End-to-End Event-Based DoLP Recovery Network", Photonics 2024.
"""

import numpy as np
import cv2
from typing import Dict, Tuple


def hsv_to_polarization(rgb: np.ndarray,
                        polarization_strength: float = 1.0,
                        add_noise: bool = True,
                        noise_level: float = 0.02) -> Dict[str, np.ndarray]:
    """Simulate 4 polarization channels from RGB via HSV color space mapping.

    The core assumption (from Yan et al. 2024):
    - Hue maps to polarization angle: different colored structures
      (cell walls, chloroplasts, vacuoles) have different optical
      anisotropy orientations.
    - Saturation maps to polarization degree: more saturated regions
      (pigment-dense) exhibit stronger polarization response.
    - Value maps to total intensity S₀.

    Args:
        rgb: Input RGB image (H, W, 3), uint8 [0, 255].
        polarization_strength: Global multiplier for DoLP.
        add_noise: Add photon shot noise.
        noise_level: Noise standard deviation relative to intensity.

    Returns:
        Dict with keys "I0", "I45", "I90", "I135" (uint8),
        plus "S0", "DoLP", "AoP" (float intermediates).
    """
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    h, w = rgb.shape[:2]

    # ── RGB → HSV ──────────────────────────────────────────
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)

    H = hsv[:, :, 0]          # [0, 180)  → AoP
    S = hsv[:, :, 1] / 255.0  # [0, 1]    → DoLP
    V = hsv[:, :, 2] / 255.0  # [0, 1]    → S₀

    # ── Map HSV to Stokes-analogue parameters ──────────────
    AoP = H * np.pi / 180.0            # [0, π)
    DoLP = S * polarization_strength    # [0, 1]
    S0 = V                              # [0, 1]

    # Suppress DoLP where V is very low (noise-dominated, H/S unreliable)
    dark_mask = V < 0.05
    DoLP[dark_mask] *= (V[dark_mask] / 0.05)

    # ── Periodic-aware AoP encoding (for physical consistency) ──
    cos_2aop = np.cos(2 * AoP)
    sin_2aop = np.sin(2 * AoP)

    # ── Compute 4 polarization channels via Stokes formula ──
    # I(θ) = ½ S₀ (1 + DoLP · cos(2(θ − AoP)))
    # cos(2(θ − AoP)) = cos(2θ − 2AoP) = cos(2θ)cos(2AoP) + sin(2θ)sin(2AoP)

    angles_deg = [0, 45, 90, 135]
    channels = {}

    for angle in angles_deg:
        theta = np.deg2rad(angle)
        cos_2theta = np.cos(2 * theta)
        sin_2theta = np.sin(2 * theta)

        cos_diff = cos_2theta * cos_2aop + sin_2theta * sin_2aop
        I_theta = 0.5 * S0 * (1.0 + DoLP * cos_diff)

        # Clip and convert
        I_theta = np.clip(I_theta, 0, 1)
        channels[f"I{angle}"] = (I_theta * 255).astype(np.uint8)

    # ── Add shot noise ─────────────────────────────────────
    if add_noise:
        rng = np.random.default_rng(42)
        for key in [f"I{a}" for a in angles_deg]:
            ch = channels[key].astype(np.float32)
            noise = rng.normal(0, noise_level * 255, (h, w)).astype(np.float32)
            channels[key] = np.clip(ch + noise, 0, 255).astype(np.uint8)

    # Attach intermediates for inspection
    channels["S0"] = (S0 * 255).astype(np.uint8)
    channels["DoLP"] = (DoLP * 255).astype(np.uint8)
    channels["AoP"] = (AoP / np.pi * 255).astype(np.uint8)

    return channels


def create_preview(channels: Dict[str, np.ndarray]) -> np.ndarray:
    """Create a 2×3 preview grid: I0 | I45 | I90 | I135 | S0 | DoLP."""
    keys = ["I0", "I45", "I90", "I135", "S0", "DoLP"]
    tiles = []
    for key in keys:
        img = channels[key]
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        tiles.append(img)

    row1 = np.hstack(tiles[:3])
    row2 = np.hstack(tiles[3:])

    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    for i, (row, start_idx) in enumerate([(row1, 0), (row2, 3)]):
        for j, key in enumerate(keys[start_idx:start_idx + 3]):
            x = j * tiles[0].shape[1] + 5
            y = 20
            cv2.putText(row, key, (x, y), font, 0.5, (0, 255, 0), 1)

    return np.vstack([row1, row2])


def batch_simulate_hsv(image_paths: list, **kwargs) -> list:
    """Batch-process a list of image paths through HSV polarization."""
    results = []
    for path in image_paths:
        img = cv2.imread(str(path))
        if img is None:
            print(f"  [SKIP] Cannot read {path}")
            continue
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        channels = hsv_to_polarization(rgb, **kwargs)
        results.append((path, channels))
    return results


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Quick test with a sample image
    sample_dir = Path(__file__).resolve().parents[1] / "code" / "algae_guardian" / \
                 "data" / "download" / "extracted" / "dataset" / "dataset"
    samples = sorted(sample_dir.glob("*.tif"))[:3]

    if not samples:
        print("No sample images found. Provide an image path as argument.")
        sys.exit(1)

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)

    for sample in samples:
        print(f"Processing {sample.name}...")
        img = cv2.imread(str(sample))
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ch = hsv_to_polarization(rgb)

        preview = create_preview(ch)
        out_path = out_dir / f"hsv_preview_{sample.stem}.jpg"
        cv2.imwrite(str(out_path), preview)
        print(f"  Saved {out_path}")

    print("Done.")
