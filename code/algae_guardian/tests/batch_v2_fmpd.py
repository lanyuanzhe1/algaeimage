"""Batch process all FMPD TIFF images through the v2 polarization pipeline.

Saves ALL intermediate channels + final pseudo-color YOLO input.

Input:  data/fmpd_download/extracted/dataset/dataset/*.tif
Output: data/fmpd_rdn_output_v2/
    ├── s0/          S0 (total intensity, uint8 grayscale)
    ├── s1/          S1 (0/90 difference, normalized)
    ├── s2/          S2 (45/135 difference, normalized)
    ├── dolp/        DoLP (degree of linear polarization heatmap)
    ├── aop/         AoP (angle of polarization heatmap)
    ├── ienh/        I_enh (v2 polarization enhancement, uint8 grayscale)
    ├── corrected/   Backscatter-corrected (uint8 grayscale)
    ├── images/      Final 3-channel pseudo-color (YOLO input)
    ├── preview/     S0|S1|S2 side-by-side + AoP grayscale + DoLP grayscale
    └── summary_{timestamp}.json
"""
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))

from image_processing.polarization_sim import simulate_polarization_from_rgb_v2

# ── Config ──
PROJECT_ROOT = Path(__file__).parent.parent
TIFF_DIR = PROJECT_ROOT / "data" / "download" / "extracted" / "dataset" / "dataset"
V2_ROOT = PROJECT_ROOT / "data" / "rdn_output_v2"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")  # for summary JSON only

# Subdirectory per channel
os.makedirs(V2_ROOT, exist_ok=True)
SUBDIRS = ["s0", "s1", "s2", "dolp", "aop", "ienh", "corrected", "images", "preview"]
for sd in SUBDIRS:
    os.makedirs(V2_ROOT / sd, exist_ok=True)


def save_gray(arr, subdir, stem, vmin=None, vmax=None):
    """Save a float32/uint8 array as grayscale PNG."""
    fname = f"{stem}.png"
    fpath = V2_ROOT / subdir / fname
    arr_f = arr.astype(np.float32)
    lo = vmin if vmin is not None else arr_f.min()
    hi = vmax if vmax is not None else arr_f.max()
    if hi - lo < 1e-10:
        out = np.zeros_like(arr_f, dtype=np.uint8)
    else:
        out = ((arr_f - lo) / (hi - lo) * 255).astype(np.uint8)
    ok = cv2.imwrite(str(fpath), out)
    if not ok:
        raise IOError(f"cv2.imwrite failed: {fpath}")
    return fpath


def save_heatmap(arr, subdir, stem, colormap=cv2.COLORMAP_JET):
    """Save a float32 array as color-mapped PNG."""
    fname = f"{stem}.png"
    fpath = V2_ROOT / subdir / fname
    arr_f = arr.astype(np.float32)
    lo, hi = arr_f.min(), arr_f.max()
    if hi - lo < 1e-10:
        out = np.zeros_like(arr_f, dtype=np.uint8)
    else:
        out = ((arr_f - lo) / (hi - lo) * 255).astype(np.uint8)
    colored = cv2.applyColorMap(out, colormap)
    ok = cv2.imwrite(str(fpath), colored)
    if not ok:
        raise IOError(f"cv2.imwrite failed: {fpath}")
    return fpath


def _clahe(gray):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _add_label(img, text, pos=(10, 30)):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, pos, font, 0.8, (0, 0, 0), 4)
    cv2.putText(img, text, pos, font, 0.8, (255, 255, 255), 2)


def make_preview_stokes(S0, S1, S2):
    """S0|S1|S2 side-by-side, CLAHE per panel. S0=S0_norm(uint8), S1/S2=float32 signed."""
    def _norm(x):
        x_min, x_max = x.min(), x.max()
        if x_max - x_min < 1e-10:
            return np.zeros_like(x, dtype=np.uint8)
        return ((x - x_min) / (x_max - x_min) * 255).astype(np.uint8)

    s0_panel = np.stack([_clahe(S0)] * 3, axis=-1)
    s1_panel = np.stack([_clahe(_norm(S1))] * 3, axis=-1)
    s2_panel = np.stack([_clahe(_norm(S2))] * 3, axis=-1)

    h, w = s0_panel.shape[:2]
    divider = np.full((h, 3, 3), 255, dtype=np.uint8)
    img = np.concatenate([s0_panel, divider, s1_panel, divider, s2_panel], axis=1)

    _add_label(img, "S0", (8, 28))
    _add_label(img, "S1", (w + 11, 28))
    _add_label(img, "S2", (2 * w + 14, 28))
    return img


def make_preview_aop_gray(AoP):
    """AoP grayscale: normalize [-π/2,π/2] → uint8 + CLAHE."""
    lo, hi = AoP.min(), AoP.max()
    if hi - lo < 1e-10:
        norm = np.zeros_like(AoP, dtype=np.uint8)
    else:
        norm = ((AoP - lo) / (hi - lo) * 255).astype(np.uint8)
    return _clahe(norm)


def make_preview_dolp(DoLP):
    """DoLP grayscale: CLAHE + gamma 0.7."""
    norm = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
    enhanced = _clahe(norm)
    enhanced = (np.power(enhanced / 255.0, 0.7) * 255).astype(np.uint8)
    return enhanced


def main():
    tiff_files = sorted(TIFF_DIR.glob("*.tif"))
    if not tiff_files:
        print(f"No TIFF files found in {TIFF_DIR}")
        return

    print(f"Found {len(tiff_files)} TIFF files")
    print(f"Output root: {V2_ROOT}")
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Subdirs: {SUBDIRS}")
    print("=" * 60)

    summary = []
    success = 0
    failed = 0
    t_start = time.time()

    for i, tiff_path in enumerate(tiff_files):
        stem = tiff_path.stem
        print(f"[{i+1}/{len(tiff_files)}] {stem} ...", end=" ", flush=True)

        try:
            img_bgr = cv2.imread(str(tiff_path))
            if img_bgr is None:
                print("SKIP: cannot read")
                failed += 1
                continue
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            t_img = time.time()
            final, inter = simulate_polarization_from_rgb_v2(
                img_rgb,
                polarization_strength=1.0,
                use_reconstructor=True,
                alpha=0.6, beta=0.25, gamma=0.35,
                return_all=True,
            )
            elapsed = (time.time() - t_img) * 1000

            # ── Save all intermediate channels ──
            save_gray(inter["S0"], "s0", stem)
            save_gray(inter["S1"], "s1", stem)
            save_gray(inter["S2"], "s2", stem)
            save_gray(inter["DoLP"], "dolp", stem, vmin=0, vmax=1)
            save_gray(inter["AoP"], "aop", stem)
            save_gray(inter["I_enh"], "ienh", stem)
            save_gray(inter["corrected"], "corrected", stem)

            # ── Preview: S0|S1|S2 side-by-side + AoP gray + DoLP gray ──
            # S0 from inter is already uint8; S1/S2 are float32 signed
            stokes_preview = make_preview_stokes(inter["S0"], inter["S1"], inter["S2"])
            aop_preview = make_preview_aop_gray(inter["AoP"])
            dolp_preview = make_preview_dolp(inter["DoLP"])
            cv2.imwrite(str(V2_ROOT / "preview" / f"{stem}_stokes.jpg"),
                        cv2.cvtColor(stokes_preview, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(V2_ROOT / "preview" / f"{stem}_aop.jpg"), aop_preview)
            cv2.imwrite(str(V2_ROOT / "preview" / f"{stem}_dolp.jpg"), dolp_preview)

            # Final 3-channel pseudo-color (YOLO input)
            fname = f"{stem}.jpg"
            fpath = V2_ROOT / "images" / fname
            cv2.imwrite(str(fpath), cv2.cvtColor(final, cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])

            r_mean, g_mean, b_mean = final[:,:,0].mean(), final[:,:,1].mean(), final[:,:,2].mean()
            print(f"OK ({elapsed:.0f}ms)  RGB=({r_mean:.0f},{g_mean:.0f},{b_mean:.0f})")
            summary.append({
                "input": stem,
                "shape": list(img_rgb.shape),
                "time_ms": round(elapsed, 1),
                "final_rgb_mean": [round(r_mean,1), round(g_mean,1), round(b_mean,1)],
            })
            success += 1

        except Exception as e:
            print(f"FAIL: {e}")
            import traceback
            traceback.print_exc()
            summary.append({"input": stem, "error": str(e)})
            failed += 1

    # ── Summary ──
    total_elapsed = (time.time() - t_start) / 60
    print(f"\n{'=' * 60}")
    print(f"Done. {success}/{len(tiff_files)} success, {failed} failed in {total_elapsed:.1f} min")

    summary_path = V2_ROOT / f"summary_{TIMESTAMP}.json"
    summary_data = {
        "timestamp": TIMESTAMP,
        "pipeline": "v2",
        "formula": "I_enh = Norm( S0_norm * (1 + alpha - gamma*DoLP + beta * |sin(2*AoP)| * DoLP) )",
        "params": {"alpha": 0.6, "beta": 0.25, "gamma": 0.35},
        "fixes": [
            "DoLP clipped to [0,1] (was exploding to 1e12)",
            "B-channel normalized same as R/G (was un-normalized clip)",
            "I_enh: DoLP subtraction for dehazing, |sin(2*AoP)| for continuous circular mapping",
        ],
        "subdirs": SUBDIRS,
        "total": len(tiff_files),
        "success": success,
        "failed": failed,
        "elapsed_min": round(total_elapsed, 1),
        "results": summary,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
