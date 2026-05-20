"""Simulate polarization channels (0°, 45°, 90°) from RGB microscopy images.

Implements the gradient-based pseudo-polarization method:
    - Structure tensor analysis for local orientation
    - Anisotropy-based polarization response
    - Generates physically plausible I0, I45, I90 from standard RGB

Reference: "A Method for Generating Pseudo-Polarization Images"
           IEEE Signal Processing Letters, 2024

This module enables training YOLO on standard microscopic algae datasets
(e.g., LifeWatch, FMPD) while simulating the effect of the DoFP polarization
imaging system described in the proposal.
"""
import numpy as np
import cv2
from typing import Dict, Tuple, Optional


def structure_tensor(gray: np.ndarray, sigma: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute structure tensor and derive edge orientation and anisotropy.

    Args:
        gray: Grayscale image (H, W)
        sigma: Gaussian smoothing sigma

    Returns:
        orientation: Dominant local orientation in radians [0, π)
        anisotropy: Degree of anisotropy [0, 1], where 1 = strong edge
        edge_strength: Gradient magnitude
    """
    # Compute gradients
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    # Structure tensor components
    Jxx = cv2.GaussianBlur(gx * gx, (0, 0), sigma)
    Jxy = cv2.GaussianBlur(gx * gy, (0, 0), sigma)
    Jyy = cv2.GaussianBlur(gy * gy, (0, 0), sigma)

    # Edge strength
    edge_strength = np.sqrt(Jxx + Jyy)

    # Eigenvalues
    trace = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    sqrt_discriminant = np.sqrt(np.maximum(trace * trace / 4 - det, 0))

    lambda1 = trace / 2 + sqrt_discriminant
    lambda2 = np.maximum(trace / 2 - sqrt_discriminant, 0)

    # Anisotropy
    denom = lambda1 + lambda2 + 1e-10
    anisotropy = (lambda1 - lambda2) / denom
    anisotropy = np.clip(anisotropy, 0, 1)

    # Orientation (angle of dominant eigenvector)
    orientation = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)
    # Map to [0, π)
    orientation = np.mod(orientation, np.pi)

    return orientation, anisotropy, edge_strength


def simulate_polarization_channels(rgb: np.ndarray,
                                   polarization_strength: float = 1.0,
                                   sigma: float = 2.0,
                                   add_shot_noise: bool = True,
                                   noise_level: float = 0.02) -> Dict[str, np.ndarray]:
    """Simulate 0°, 45°, 90°, 135° polarization channels from an RGB image.

    The simulation models how a DoFP polarization camera would capture
    microalgae under dark-field illumination. The key insight is that
    edges, cell boundaries, and structural features of algae produce
    stronger polarization responses, while flat regions and background
    remain unpolarized.

    All 4 channels follow the same Malus law: I(θ) = I_base × (1 + P × cos²(θ - θ_local)).
    This ensures physically consistent I135 (not interpolated from I0/I90).

    Args:
        rgb: Input RGB image (H, W, 3), uint8 [0, 255]
        polarization_strength: Overall polarization effect multiplier
        sigma: Gaussian smoothing for structure tensor
        add_shot_noise: Whether to add realistic photon shot noise
        noise_level: Shot noise level (fraction of intensity)

    Returns:
        Dict with "I0", "I45", "I90", "I135" channels (uint8)
    """
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Compute structure tensor features
    orientation, anisotropy, edge_strength = structure_tensor(gray, sigma)

    # Normalize edge strength
    edge_norm = edge_strength / (edge_strength.max() + 1e-10)

    # Base intensity (use luminance)
    I_base = gray / 255.0  # [0, 1]

    # Polarization modulation factor: edges + anisotropy
    # Algae cells have higher polarization response at boundaries
    P = anisotropy * edge_norm * polarization_strength

    # Simulate 4 polarization angles
    # I(θ) = I_base * (1 + P * cos²(orientation - θ))
    cos2_0 = np.cos(2 * (orientation - 0 * np.pi / 180))
    cos2_45 = np.cos(2 * (orientation - 45 * np.pi / 180))
    cos2_90 = np.cos(2 * (orientation - 90 * np.pi / 180))
    cos2_135 = np.cos(2 * (orientation - 135 * np.pi / 180))

    I0 = I_base * (1.0 + P * cos2_0)
    I45 = I_base * (1.0 + P * cos2_45)
    I90 = I_base * (1.0 + P * cos2_90)
    I135 = I_base * (1.0 + P * cos2_135)

    # Add cell-specific polarization: algae cell interiors have
    # different polarization response than background
    # Use color information to identify algae regions
    green_ratio = rgb[:, :, 1].astype(np.float32) / (rgb.sum(axis=2).astype(np.float32) + 1e-10)
    algae_mask = (green_ratio > 0.33) & (gray < 200)

    # Algae regions get additional polarization diversity between channels
    algae_factor = 0.3 * polarization_strength
    I0[algae_mask] *= (1.0 + algae_factor * 0.5)
    I45[algae_mask] *= (1.0 + algae_factor * 1.0)  # strongest at 45°
    I90[algae_mask] *= (1.0 + algae_factor * 0.3)
    I135[algae_mask] *= (1.0 + algae_factor * 0.6)

    # Stack and convert to uint8
    channels = np.stack([I0, I45, I90, I135], axis=-1)
    channels = np.clip(channels * 255, 0, 255).astype(np.uint8)

    # Add realistic noise
    if add_shot_noise:
        for c in range(4):
            noise = np.random.randn(h, w) * noise_level * channels[:, :, c].astype(np.float32)
            channels[:, :, c] = np.clip(channels[:, :, c].astype(np.float32) + noise, 0, 255).astype(np.uint8)

    return {"I0": channels[:, :, 0], "I45": channels[:, :, 1],
            "I90": channels[:, :, 2], "I135": channels[:, :, 3]}


def simulate_polarization_from_rgb(rgb: np.ndarray,
                                    polarization_strength: float = 1.0,
                                    use_reconstructor: bool = True,
                                    return_all: bool = False) -> np.ndarray:
    """Full pipeline adhering to the technical proposal order:

        RGB → simulate I0/I45/I90           (模拟偏振采集)
            → PolarizationReconstructor     (偏振算法网络重建)
            → ImageEnhancer + I_enh         (图像增强与去散射)
            → output ready for YOLO

    This is the main entry point for generating training data.
    Takes an RGB microscopy image and returns a polarization-enhanced 3-channel image
    ready for YOLO training.

    Args:
        rgb: Input RGB image (H, W, 3)
        polarization_strength: Controls the simulated polarization effect
        use_reconstructor: If True, run through PolarizationReconstructor
        return_all: If True, returns all intermediate results

    Returns:
        Enhanced 3-channel image (H, W, 3) uint8
    """
    from .polarization import PolarizationProcessor
    from ml.reconstructor import PolarizationReconstructor
    from .enhancement import ImageEnhancer

    # ═══════════════════════════════════════════════
    # Step 1: 模拟偏振采集 — simulate I0, I45, I90
    # ═══════════════════════════════════════════════
    sim = simulate_polarization_channels(rgb, polarization_strength)

    I0 = sim["I0"].astype(np.float32)
    I45 = sim["I45"].astype(np.float32)
    I90 = sim["I90"].astype(np.float32)
    I135 = sim["I135"].astype(np.float32)

    # ═══════════════════════════════════════════════
    # Step 2: 偏振算法网络重建 — RDN reconstruction
    # ═══════════════════════════════════════════════
    pp = PolarizationProcessor()
    stokes = pp.reconstruct_stokes(I0, I45, I90, I135)

    if use_reconstructor:
        from ml.config import PROJECT_ROOT
        model_path = str(PROJECT_ROOT / "ml" / "models" / "rdn_polarization.pth")
        reconstructor = PolarizationReconstructor(model_path=model_path)
        # RDN reconstructs from I0, I45, I90, I135 → 3-channel enhanced output
        # If .pt weights are available, uses deep mode; else analytical fallback
        use_deep = reconstructor.load_model()
        recon_3ch = reconstructor.reconstruct(
            I0, I45, I90, I135,
            use_deep=use_deep
        )
        # Use reconstructed channels
        S0_recon = recon_3ch[:, :, 0].astype(np.float32)
        S1_recon = recon_3ch[:, :, 1].astype(np.float32) * 2 - 128
        S2_recon = recon_3ch[:, :, 2].astype(np.float32) * 2 - 128
        DoLP = np.sqrt(S1_recon**2 + S2_recon**2) / (S0_recon + 1e-10)
        AoP = 0.5 * np.arctan2(S2_recon, S1_recon)
        S0_use = S0_recon
    else:
        S0_use = stokes["S0"]
        DoLP = stokes["DoLP"]
        AoP = stokes["AoP"]

    # ═══════════════════════════════════════════════
    # Step 3: 图像增强与去散射 — I_enh + CLAHE + dehaze
    # ═══════════════════════════════════════════════
    # 3a: Polarization enhancement (I_enh formula)
    enhanced = pp.polarization_enhancement(S0_use, DoLP, AoP)

    # 3b: Backscatter suppression
    corrected = pp.suppress_backscatter(S0_use, DoLP)

    # 3c: Full image enhancement pipeline
    enhancer = ImageEnhancer()
    S0_norm = ((S0_use - S0_use.min()) / (S0_use.max() - S0_use.min() + 1e-10) * 255).astype(np.uint8)

    # Stack 3 channels from the reconstruction → RGB
    recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
    final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)

    if return_all:
        return final, {
            "I0": sim["I0"], "I45": sim["I45"], "I90": sim["I90"],
            "S0": S0_norm, "DoLP": DoLP, "AoP": AoP,
            "enhanced": enhanced, "corrected": corrected,
        }
    return final


def simulate_polarization_from_rgb_v2(rgb: np.ndarray,
                                       polarization_strength: float = 1.0,
                                       use_reconstructor: bool = True,
                                       alpha: float = 0.6,
                                       beta: float = 0.25,
                                       gamma: float = 0.35,
                                       return_all: bool = False) -> np.ndarray:
    """v2 pipeline: same flow, improved I_enh formula with DoLP subtraction.

    Key changes vs v1:
        I_enh_v2 = Norm( S0_norm * (1 + α - γ*DoLP + β * |sin(2*AoP)| * DoLP) )
        - DoLP is subtracted (dehazing) instead of added
        - AoP uses |sin(2*AoP)| for continuous circular mapping
        - All components operate on S0 directly, single final normalization

    Args:
        rgb: Input RGB image (H, W, 3)
        polarization_strength: Simulated polarization effect
        use_reconstructor: Run through RDN reconstructor
        alpha: Base S0 boost (default: 0.6)
        beta: AoP structure enhancement (default: 0.25)
        gamma: DoLP dehazing strength (default: 0.35)
        return_all: Return intermediates

    Returns:
        Enhanced 3-channel image (H, W, 3) uint8
    """
    from .polarization import PolarizationProcessor
    from ml.reconstructor import PolarizationReconstructor
    from .enhancement import ImageEnhancer

    # Step 1: Polarization simulation (same as v1)
    sim = simulate_polarization_channels(rgb, polarization_strength)
    I0 = sim["I0"].astype(np.float32)
    I45 = sim["I45"].astype(np.float32)
    I90 = sim["I90"].astype(np.float32)
    I135 = sim["I135"].astype(np.float32)

    # Step 2: Stokes + RDN reconstruction (same as v1)
    pp = PolarizationProcessor()
    stokes = pp.reconstruct_stokes(I0, I45, I90, I135)

    if use_reconstructor:
        from ml.config import PROJECT_ROOT
        model_path = str(PROJECT_ROOT / "ml" / "models" / "rdn_polarization.pth")
        reconstructor = PolarizationReconstructor(model_path=model_path)
        use_deep = reconstructor.load_model()
        recon_3ch = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=use_deep)
        S0_recon = recon_3ch[:, :, 0].astype(np.float32)
        S1_recon = recon_3ch[:, :, 1].astype(np.float32) * 2 - 128
        S2_recon = recon_3ch[:, :, 2].astype(np.float32) * 2 - 128
        DoLP = np.sqrt(S1_recon**2 + S2_recon**2) / (S0_recon + 1e-10)
        DoLP = np.clip(DoLP, 0, 1)
        AoP = 0.5 * np.arctan2(S2_recon, S1_recon)
        S0_use = S0_recon
    else:
        S0_use = stokes["S0"]
        DoLP = stokes["DoLP"]
        AoP = stokes["AoP"]

    # Step 3a: I_enh v2 (the key change)
    enhanced = pp.polarization_enhancement_v2(S0_use, DoLP, AoP,
                                               alpha=alpha, beta=beta, gamma=gamma)

    # Step 3b: Backscatter suppression — normalize same as S0 for channel balance
    corrected_raw = S0_use * (1.0 - 0.5 * DoLP.astype(np.float32))
    corrected = ((corrected_raw - corrected_raw.min()) /
                 (corrected_raw.max() - corrected_raw.min() + 1e-10) * 255).astype(np.uint8)

    # Step 3c: Stack + CLAHE — all 3 channels now share the same normalization scheme
    enhancer = ImageEnhancer()
    S0_norm = ((S0_use - S0_use.min()) / (S0_use.max() - S0_use.min() + 1e-10) * 255).astype(np.uint8)
    recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
    final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)

    if return_all:
        return final, {
            "S0": S0_norm, "S1": S1_recon, "S2": S2_recon,
            "DoLP": DoLP, "AoP": AoP,
            "I_enh": enhanced, "corrected": corrected,
        }
    return final


def batch_simulate(image_list, polarization_strength: float = 1.0):
    """Batch process a list of RGB images through the polarization simulator."""
    results = []
    for img in image_list:
        result = simulate_polarization_from_rgb(img, polarization_strength)
        results.append(result)
    return results


def prepare_yolo_dataset(input_dir: str,
                          output_dir: str,
                          polarization_strength: float = 1.0,
                          image_ext: str = ".png",
                          label_ext: str = ".txt"):
    """Process an entire dataset through the polarization pipeline for YOLO training.

    Expects YOLO-format dataset structure:
        input_dir/
            images/train/
            images/val/
            labels/train/
            labels/val/

    Output:
        output_dir/
            images/train/   (polarization-enhanced)
            images/val/     (polarization-enhanced)
            labels/train/   (copied from input, unchanged)
            labels/val/     (copied from input, unchanged)
    """
    import shutil
    from pathlib import Path

    in_path = Path(input_dir)
    out_path = Path(output_dir)
    splits = ["train", "val"]

    for split in splits:
        img_dir = in_path / "images" / split
        if not img_dir.exists():
            print(f"  [SKIP] {img_dir} not found")
            continue

        out_img_dir = out_path / "images" / split
        out_label_dir = out_path / "labels" / split
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_label_dir.mkdir(parents=True, exist_ok=True)

        img_files = sorted(img_dir.glob(f"*{image_ext}")) + sorted(img_dir.glob("*.jpg"))
        print(f"  Processing {split}: {len(img_files)} images...")

        for i, img_path in enumerate(img_files):
            # Read image
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Run polarization pipeline
            result = simulate_polarization_from_rgb(img_rgb, polarization_strength)
            result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

            # Save enhanced image
            out_img_path = out_img_dir / img_path.name
            cv2.imwrite(str(out_img_path), result_bgr)

            # Copy label file if exists
            label_path = in_path / "labels" / split / img_path.with_suffix(label_ext).name
            if label_path.exists():
                shutil.copy(str(label_path), str(out_label_dir / label_path.name))

            if (i + 1) % 100 == 0:
                print(f"    {i + 1}/{len(img_files)}")

        print(f"  [DONE] {split}: {len(img_files)} images")
