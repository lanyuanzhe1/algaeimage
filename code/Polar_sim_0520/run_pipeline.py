"""HSV vs Structure-Tensor polarization pipeline on FMPD dataset.

Pipeline stages (each saved to disk):
    Stage 1: RGB → 4-ch polarization .npz
        → output/polarization_hsv/   (HSV method)
        → output/polarization_struct/(structure tensor)
    Stage 2: 4-ch .npz → RDN reconstruction → 3-ch enhanced
        → output/rdn_output_hsv/
        → output/rdn_output_struct/
    Stage 3: RDN output → I_enh v2 + CLAHE → final 3-ch YOLO input
        → output/yolo_input_hsv/
        → output/yolo_input_struct/
    Stage 4: Side-by-side preview
        → output/comparisons/

No original code is modified. All dependencies copied into this folder.
"""

import sys
import os
import json
import time
from pathlib import Path
import numpy as np
import cv2

# ── Isolated imports from local copies ─────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsv_polarization import hsv_to_polarization
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from image_processing.polarization_sim import simulate_polarization_channels
from ml.reconstructor import PolarizationReconstructor

# ── Paths ──────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
FMPD_DIR = BASE.parent / "algae_guardian" / "data" / "download" / "extracted" / "dataset" / "dataset"
RDN_MODEL = BASE / "ml" / "models" / "rdn_polarization.pth"


def stage1_polarization(rgb: np.ndarray, method: str,
                         pol_strength: float) -> dict:
    """Stage 1: RGB → 4-channel polarization.

    Returns dict with I0, I45, I90, I135 as uint8.
    """
    if method == "hsv":
        return hsv_to_polarization(rgb, polarization_strength=pol_strength)
    else:
        return simulate_polarization_channels(rgb, polarization_strength=pol_strength)


def stage2_rdn(I0: np.ndarray, I45: np.ndarray, I90: np.ndarray,
               I135: np.ndarray, reconstructor: PolarizationReconstructor,
               pp: PolarizationProcessor) -> dict:
    """Stage 2: 4-ch polarization → RDN → Stokes parameters.

    Returns dict with S0_recon, DoLP_recon, AoP_recon, raw_RDN_output.
    """
    # RDN: 4ch → 4ch
    use_deep = reconstructor.is_available()
    recon_4ch = reconstructor.reconstruct(
        I0.astype(np.float32), I45.astype(np.float32),
        I90.astype(np.float32), I135.astype(np.float32),
        use_deep=use_deep
    )

    # Proper Stokes from RDN-enhanced 4-channel (joint-normalized, ratios preserved)
    # RDN output = enhanced I0'/I45'/I90'/I135'
    I0_r = recon_4ch[:, :, 0].astype(np.float32)
    I45_r = recon_4ch[:, :, 1].astype(np.float32)
    I90_r = recon_4ch[:, :, 2].astype(np.float32)
    I135_r = recon_4ch[:, :, 3].astype(np.float32)

    S0_recon = I0_r + I90_r
    S1_recon = I0_r - I90_r
    S2_recon = I45_r - I135_r
    DoLP = np.clip(np.sqrt(S1_recon**2 + S2_recon**2) / (S0_recon + 1e-10), 0, 1)
    AoP = 0.5 * np.arctan2(S2_recon, S1_recon)

    return {
        "rdn_4ch": recon_4ch,
        "S0_recon": S0_recon,
        "DoLP_recon": DoLP,
        "AoP_recon": AoP,
    }


def stage3_enhance(rdn_result: dict, pp: PolarizationProcessor,
                   enhancer: ImageEnhancer) -> np.ndarray:
    """Stage 3: Stokes → I_enh v2 + CLAHE → final 3-ch YOLO input."""
    S0 = rdn_result["S0_recon"]
    DoLP = rdn_result["DoLP_recon"]
    AoP = rdn_result["AoP_recon"]

    # I_enh v2
    enhanced = pp.polarization_enhancement_v2(S0, DoLP, AoP,
                                               alpha=0.6, beta=0.25, gamma=0.35)
    # Backscatter suppression
    corrected_raw = S0 * (1.0 - 0.5 * DoLP.astype(np.float32))
    corrected = ((corrected_raw - corrected_raw.min()) /
                 (corrected_raw.max() - corrected_raw.min() + 1e-10) * 255).astype(np.uint8)

    # S0 normalize
    S0_norm = ((S0 - S0.min()) / (S0.max() - S0.min() + 1e-10) * 255).astype(np.uint8)

    # 3-ch stack + CLAHE
    recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
    final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)
    return final


def make_comparison(rgb: np.ndarray, p_hsv: dict, p_struct: dict,
                    r_hsv: dict, r_struct: dict,
                    f_hsv: np.ndarray, f_struct: np.ndarray,
                    title: str = "") -> np.ndarray:
    """Create 4-row comparison panel."""
    h, w = rgb.shape[:2]
    scale = 350 / max(h, w)
    nh, nw = int(h * scale), int(w * scale)

    def rs(img):
        if img is None:
            return np.zeros((nh, nw, 3), dtype=np.uint8)
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        return cv2.resize(img, (nw, nh))

    def tag(im, txt):
        cv2.putText(im, txt, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        return im

    def dolp_viz(arr):
        """Make DoLP visible."""
        if arr.max() <= 1.0:
            arr = (arr * 255).astype(np.uint8)
        elif arr.dtype != np.uint8:
            arr = ((arr - arr.min()) / (arr.max() - arr.min() + 1e-10) * 255).astype(np.uint8)
        return arr

    def get_s0(pol):
        return pol.get("S0", pol["I0"].astype(np.float32) + pol["I90"].astype(np.float32))

    def get_dolp(pol):
        if "DoLP" in pol:
            return pol["DoLP"]
        I0 = pol["I0"].astype(np.float32)
        I45 = pol["I45"].astype(np.float32)
        I90 = pol["I90"].astype(np.float32)
        I135 = pol["I135"].astype(np.float32)
        return np.clip(np.sqrt((I0-I90)**2 + (I45-I135)**2) / (I0+I90+1e-10), 0, 1)

    r1 = np.hstack([tag(rs(rgb), "Original"),
                    tag(rs(p_hsv["I0"]), "HSV-I0"),
                    tag(rs(p_hsv["I45"]), "HSV-I45"),
                    tag(rs(p_hsv["I90"]), "HSV-I90"),
                    tag(rs(p_hsv["I135"]), "HSV-I135")])

    r2 = np.hstack([tag(rs(p_struct["I0"]), "Struct-I0"),
                    tag(rs(p_struct["I45"]), "Struct-I45"),
                    tag(rs(p_struct["I90"]), "Struct-I90"),
                    tag(rs(p_struct["I135"]), "Struct-I135"),
                    tag(rs(dolp_viz(r_hsv["DoLP_recon"])), "HSV-DoLP")])

    r3 = np.hstack([tag(rs(dolp_viz(r_struct["DoLP_recon"])), "Struct-DoLP"),
                    tag(rs(r_hsv["rdn_4ch"][:, :, :3]), "HSV-RDN"),
                    tag(rs(r_struct["rdn_4ch"][:, :, :3]), "Struct-RDN"),
                    tag(rs(f_hsv), "HSV-FINAL"),
                    tag(rs(f_struct), "Struct-FINAL")])

    r4 = np.hstack([tag(rs(get_s0(p_hsv)), "HSV-S0"),
                    tag(rs(dolp_viz(get_dolp(p_hsv))), "HSV-DoLP_raw"),
                    tag(rs(get_s0(p_struct)), "Struct-S0"),
                    tag(rs(dolp_viz(get_dolp(p_struct))), "Struct-DoLP_raw"),
                    np.zeros((nh, nw, 3), dtype=np.uint8)])

    out = np.vstack([r1, r2, r3, r4])
    if title:
        cv2.putText(out, title, (10, out.shape[0] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="HSV vs Struct polarization pipeline")
    parser.add_argument("--num-samples", type=int, default=0,
                        help="Number of samples (0=all 293)")
    parser.add_argument("--pol-strength", type=float, default=1.0)
    parser.add_argument("--skip-struct", action="store_true",
                        help="Skip structure tensor method (faster)")
    args = parser.parse_args()

    samples = sorted(FMPD_DIR.glob("*.tif"))
    if args.num_samples > 0:
        samples = samples[:args.num_samples]

    print(f"{'='*55}")
    print(f"Polarization Pipeline: HSV vs Structure Tensor")
    print(f"{'='*55}")
    print(f"Samples: {len(samples)}")
    print(f"RDN: {RDN_MODEL}")
    print(f"Skip struct: {args.skip_struct}")
    print()

    # ── Output directories ────────────────────────────
    dirs = {
        "pol_hsv":    OUTPUT / "polarization_hsv",
        "pol_struct": OUTPUT / "polarization_struct",
        "rdn_hsv":    OUTPUT / "rdn_output_hsv",
        "rdn_struct": OUTPUT / "rdn_output_struct",
        "yolo_hsv":   OUTPUT / "yolo_input_hsv",
        "yolo_struct":OUTPUT / "yolo_input_struct",
        "comp":       OUTPUT / "comparisons",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # ── Load models once ─────────────────────────────
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:256"
        print(f"GPU: {gpu_name} ({vram:.1f} GB)")

    print("Loading RDN...")
    reconstructor = PolarizationReconstructor(model_path=str(RDN_MODEL), device=device)
    reconstructor.load_model()
    print(f"  Loaded: {reconstructor.is_available()}, device={device}\n")

    pp = PolarizationProcessor()
    enhancer = ImageEnhancer()

    # ── Process ──────────────────────────────────────
    SLEEP_BETWEEN = 0.3   # throttle GPU duty cycle
    t0 = time.time()
    stats = []

    for i, sample in enumerate(samples):
        stem = sample.stem
        print(f"[{i+1:3d}/{len(samples)}] {stem}...", end=" ", flush=True)

        img = cv2.imread(str(sample))
        if img is None:
            print("SKIP")
            continue
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        row = {"stem": stem}

        # === HSV Method ===
        # Stage 1: RGB → polarization
        p_hsv = stage1_polarization(rgb, "hsv", args.pol_strength)
        np.savez_compressed(
            dirs["pol_hsv"] / f"{stem}.npz",
            I0=p_hsv["I0"], I45=p_hsv["I45"],
            I90=p_hsv["I90"], I135=p_hsv["I135"],
        )

        # Stage 2: polarization → RDN
        r_hsv = stage2_rdn(p_hsv["I0"], p_hsv["I45"], p_hsv["I90"], p_hsv["I135"],
                           reconstructor, pp)
        cv2.imwrite(str(dirs["rdn_hsv"] / f"{stem}.jpg"),
                    cv2.cvtColor(r_hsv["rdn_4ch"][:, :, :3], cv2.COLOR_RGB2BGR))

        # Stage 3: RDN → YOLO input
        f_hsv = stage3_enhance(r_hsv, pp, enhancer)
        cv2.imwrite(str(dirs["yolo_hsv"] / f"{stem}.jpg"),
                    cv2.cvtColor(f_hsv, cv2.COLOR_RGB2BGR))

        row["hsv_dolp"] = float(r_hsv["DoLP_recon"].mean())
        row["hsv_enh"] = float(f_hsv.mean())

        # === Structure Tensor Method ===
        if not args.skip_struct:
            p_struct = stage1_polarization(rgb, "struct", args.pol_strength)
            np.savez_compressed(
                dirs["pol_struct"] / f"{stem}.npz",
                I0=p_struct["I0"], I45=p_struct["I45"],
                I90=p_struct["I90"], I135=p_struct["I135"],
            )

            r_struct = stage2_rdn(p_struct["I0"], p_struct["I45"],
                                  p_struct["I90"], p_struct["I135"],
                                  reconstructor, pp)
            cv2.imwrite(str(dirs["rdn_struct"] / f"{stem}.jpg"),
                        cv2.cvtColor(r_struct["rdn_4ch"][:, :, :3], cv2.COLOR_RGB2BGR))

            f_struct = stage3_enhance(r_struct, pp, enhancer)
            cv2.imwrite(str(dirs["yolo_struct"] / f"{stem}.jpg"),
                        cv2.cvtColor(f_struct, cv2.COLOR_RGB2BGR))

            row["struct_dolp"] = float(r_struct["DoLP_recon"].mean())
            row["struct_enh"] = float(f_struct.mean())

            # Comparison preview
            comp = make_comparison(rgb, p_hsv, p_struct, r_hsv, r_struct, f_hsv, f_struct, stem)
            cv2.imwrite(str(dirs["comp"] / f"{stem}.jpg"), comp)

            p_struct = r_struct = f_struct = None  # free memory

        stats.append(row)
        p_hsv = r_hsv = f_hsv = None
        if device == "cuda":
            torch.cuda.empty_cache()
        print("OK")
        time.sleep(SLEEP_BETWEEN)

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f"Done in {elapsed:.0f}s ({elapsed/len(samples):.1f}s/img)")

    # ── Output summary ───────────────────────────────
    print(f"\nOutput structure:")
    for name, d in dirs.items():
        n = len(list(d.glob("*"))) if d.exists() else 0
        print(f"  {d.relative_to(BASE)}/  ({n} files)")

    # Stats
    if stats:
        for key in ["hsv_dolp", "struct_dolp", "hsv_enh", "struct_enh"]:
            vals = [s[key] for s in stats if key in s]
            if vals:
                print(f"  {key}: mean={np.mean(vals):.4f}, std={np.std(vals):.4f}")

        with open(OUTPUT / "stats.json", "w") as f:
            json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
