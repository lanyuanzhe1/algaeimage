"""I_enh v2 de-scattering enhancement from 4-channel polarization.

Stokes parameters computed from DoFP-style polarization:
    S0 = I0 + I90     (total intensity)
    S1 = I0 - I90     (horizontal/vertical difference)
    S2 = I45 - I135   (diagonal difference)

Enhancement formula:
    I_enh = Norm( S0 * (1 + alpha - gamma*DoLP + beta * |sin(2*AoP)| * DoLP) )

Design rationale:
    - DoLP is SUBTRACTED (dehazing/scattering suppression)
    - |sin(2*AoP)| maps AoP continuously to [0, 1], peaking at 45°/135°
    - AoP*DoLP interaction enhances edges only where polarization is meaningful
"""
import numpy as np


def compute_stokes(I_channels: np.ndarray) -> dict:
    """Compute Stokes parameters from 4-channel polarization.

    Args:
        I_channels: (4, H, W) float32 array [I0, I45, I90, I135]

    Returns:
        dict with keys: S0, S1, S2, DoLP, AoP — all float32 ndarrays
    """
    I0 = I_channels[0]
    I45 = I_channels[1]
    I90 = I_channels[2]
    I135 = I_channels[3]

    S0 = I0 + I90
    S1 = I0 - I90
    S2 = I45 - I135

    eps = 1e-8
    DoLP = np.sqrt(S1.astype(np.float64)**2 + S2.astype(np.float64)**2) / (S0.astype(np.float64) + eps)
    DoLP = np.clip(DoLP, 0.0, 1.0).astype(np.float32)

    AoP = 0.5 * np.arctan2(S2.astype(np.float64), S1.astype(np.float64) + eps)
    AoP = AoP.astype(np.float32)

    return {
        "S0": S0.astype(np.float32),
        "S1": S1.astype(np.float32),
        "S2": S2.astype(np.float32),
        "DoLP": DoLP,
        "AoP": AoP,
    }


def enhance(I_channels: np.ndarray,
            alpha: float = 0.6,
            beta: float = 0.25,
            gamma: float = 0.35) -> np.ndarray:
    """I_enh v2: de-scattering enhancement from 4-channel polarization.

    I_enh = Norm( S0 * (1 + alpha - gamma*DoLP + beta * |sin(2*AoP)| * DoLP) )

    Args:
        I_channels: (4, H, W) float32 cleaned polarization [I0, I45, I90, I135]
        alpha: Base S0 boost, default 0.6
        beta: AoP structure enhancement, default 0.25
        gamma: DoLP dehazing (scattering suppression), default 0.35

    Returns:
        (H, W) float32 enhanced grayscale image in [0, 1]
    """
    stokes = compute_stokes(I_channels)
    S0 = stokes["S0"]
    DoLP = stokes["DoLP"]
    AoP = stokes["AoP"]

    # Normalize S0 to [0, 1]
    s0_min, s0_max = S0.min(), S0.max()
    if s0_max - s0_min > 1e-10:
        S0_norm = (S0 - s0_min) / (s0_max - s0_min)
    else:
        S0_norm = np.zeros_like(S0, dtype=np.float32)

    # AoP modulation: |sin(2*AoP)| maps circular AoP to [0, 1]
    # Peaks at 45° and 135° where polarization contrast is strongest
    AoP_mod = np.abs(np.sin(2.0 * AoP))

    # Core enhancement formula
    I_enh = S0_norm * (1.0 + alpha - gamma * DoLP + beta * AoP_mod * DoLP)
    I_enh = np.clip(I_enh, 0.0, None)

    # Final normalization to [0, 1]
    enh_min, enh_max = I_enh.min(), I_enh.max()
    if enh_max - enh_min > 1e-10:
        I_enh = (I_enh - enh_min) / (enh_max - enh_min)
    else:
        I_enh = np.zeros_like(I_enh, dtype=np.float32)

    return I_enh.astype(np.float32)
