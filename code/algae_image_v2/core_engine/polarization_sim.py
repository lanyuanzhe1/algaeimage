"""Simulate 4-channel polarization from RGB using structure tensor + Malus law.

Physical model: I(theta) = I_base * (1 + P * cos^2(orientation - theta))
where P = anisotropy * edge_norm * polarization_strength.

All 4 channels (I0, I45, I90, I135) are independently computed,
ensuring S2 = I45 - I135 carries physically meaningful information.
"""
import numpy as np
import cv2


def _structure_tensor(gray: np.ndarray, sigma: float = 2.0):
    """Compute structure tensor and derive edge orientation and anisotropy.

    Args:
        gray: Grayscale image (H, W) float32
        sigma: Gaussian smoothing sigma

    Returns:
        orientation: Dominant local orientation in radians [0, pi)
        anisotropy: Degree of anisotropy [0, 1]
        edge_strength: Gradient magnitude
    """
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    Jxx = cv2.GaussianBlur(gx * gx, (0, 0), sigma)
    Jxy = cv2.GaussianBlur(gx * gy, (0, 0), sigma)
    Jyy = cv2.GaussianBlur(gy * gy, (0, 0), sigma)

    edge_strength = np.sqrt(Jxx + Jyy)

    trace = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    sqrt_discriminant = np.sqrt(np.maximum(trace * trace / 4.0 - det, 0))

    lambda1 = trace / 2.0 + sqrt_discriminant
    lambda2 = np.maximum(trace / 2.0 - sqrt_discriminant, 0)

    denom = lambda1 + lambda2 + 1e-10
    anisotropy = (lambda1 - lambda2) / denom
    anisotropy = np.clip(anisotropy, 0, 1)

    orientation = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy)
    orientation = np.mod(orientation, np.pi)

    return orientation, anisotropy, edge_strength


def simulate_polarization(rgb_image: np.ndarray,
                          polarization_strength: float = 1.0,
                          sigma: float = 2.0) -> np.ndarray:
    """Simulate 4-channel polarization from RGB using structure tensor.

    Args:
        rgb_image: (H, W, 3) uint8 RGB image
        polarization_strength: Overall polarization effect multiplier
        sigma: Gaussian smoothing sigma for structure tensor

    Returns:
        (4, H, W) float32 array: I0, I45, I90, I135, values in [0, 1]
    """
    if rgb_image.dtype != np.uint8:
        rgb_image = np.clip(rgb_image, 0, 255).astype(np.uint8)

    h, w = rgb_image.shape[:2]
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY).astype(np.float32)

    orientation, anisotropy, edge_strength = _structure_tensor(gray, sigma)

    # Normalize edge strength
    edge_norm = edge_strength / (edge_strength.max() + 1e-10)

    # Base intensity from luminance, scaled to [0, 1]
    I_base = gray / 255.0

    # Polarization modulation: edges + anisotropy create stronger response
    P = anisotropy * edge_norm * polarization_strength

    # Malus law: I(theta) = I_base * (1 + P * cos^2(orientation - theta))
    # Use cos(2*theta) form for linear polarizers
    cos2_0 = np.cos(2.0 * (orientation - 0.0 * np.pi / 180.0))
    cos2_45 = np.cos(2.0 * (orientation - 45.0 * np.pi / 180.0))
    cos2_90 = np.cos(2.0 * (orientation - 90.0 * np.pi / 180.0))
    cos2_135 = np.cos(2.0 * (orientation - 135.0 * np.pi / 180.0))

    I0 = I_base * (1.0 + P * cos2_0)
    I45 = I_base * (1.0 + P * cos2_45)
    I90 = I_base * (1.0 + P * cos2_90)
    I135 = I_base * (1.0 + P * cos2_135)

    # Algae region boost: green-dominant regions get additional polarization diversity
    rgb_sum = rgb_image.sum(axis=2).astype(np.float32)
    green_ratio = rgb_image[:, :, 1].astype(np.float32) / (rgb_sum + 1e-10)
    algae_mask = (green_ratio > 0.33) & (gray < 200)

    algae_factor = 0.3 * polarization_strength
    I0[algae_mask] *= (1.0 + algae_factor * 0.5)
    I45[algae_mask] *= (1.0 + algae_factor * 1.0)
    I90[algae_mask] *= (1.0 + algae_factor * 0.3)
    I135[algae_mask] *= (1.0 + algae_factor * 0.6)

    # Stack as (4, H, W) float32, clip to valid range
    channels = np.stack([I0, I45, I90, I135], axis=0)
    channels = np.clip(channels, 0.0, 1.0).astype(np.float32)

    return channels
