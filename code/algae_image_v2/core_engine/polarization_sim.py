"""HSV polarization simulation — V2 default (replaces structure tensor).

Maps RGB → HSV: H→AoP, S→DoLP, V→S0, then synthesizes 4-channel
I(θ) = ½S0·(1 + DoLP·cos(2(θ−AoP))) for θ ∈ {0°,45°,90°,135°}.

API matches v1: simulate_polarization(rgb) → (4, H, W) float32.
"""
import numpy as np
import cv2


def simulate_polarization(
    rgb_image: np.ndarray,
    polarization_strength: float = 1.0,
    sigma: float = 2.0,                   # kept for API compat
) -> np.ndarray:
    """HSV-based 4-channel polarization simulation.

    Args:
        rgb_image: (H, W, 3) uint8 RGB
        polarization_strength: global DoLP multiplier
        sigma: unused (API compat with structure tensor)

    Returns:
        (4, H, W) float32: I0, I45, I90, I135 in [0, 1]
    """
    if rgb_image.dtype != np.uint8:
        rgb_image = np.clip(rgb_image, 0, 255).astype(np.uint8)

    hsv = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV).astype(np.float32)

    H = hsv[:, :, 0]                # [0, 180)
    S = hsv[:, :, 1] / 255.0        # [0, 1]
    V = hsv[:, :, 2] / 255.0        # [0, 1]

    AoP = H * np.pi / 180.0         # H → AoP  [0, π)
    DoLP = S * polarization_strength
    S0_img = V

    dark_mask = V < 0.05
    DoLP[dark_mask] *= (V[dark_mask] / 0.05)

    cos_2aop = np.cos(2 * AoP)
    sin_2aop = np.sin(2 * AoP)

    angles = [0, 45, 90, 135]
    channels = np.zeros((4, *rgb_image.shape[:2]), dtype=np.float32)
    for i, angle in enumerate(angles):
        theta = np.deg2rad(angle)
        cos_diff = np.cos(2*theta)*cos_2aop + np.sin(2*theta)*sin_2aop
        I_theta = 0.5 * S0_img * (1.0 + DoLP * cos_diff)
        channels[i] = np.clip(I_theta, 0.0, 1.0).astype(np.float32)

    return channels
