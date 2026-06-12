"""Q quality scoring for polarization microscopy images.

Based on DoLP contrast and effective signal-to-noise ratio of the
reconstructed 4-channel polarization data.

Scoring formula (weighted):
    Q = w_c * C_norm + w_s * S_norm - w_n * N_norm

where:
    C_norm = normalized DoLP contrast (spread of polarization signal)
    S_norm = normalized signal strength (mean S0 energy)
    N_norm = estimated noise level from inter-channel variance
"""
import numpy as np
from .config import Q_GOOD, Q_FAIR


def compute_q_score(I_channels: np.ndarray) -> float:
    """Compute Q quality score from reconstructed polarization channels.

    Evaluates the quality of the polarization signal based on:
    - DoLP contrast: how much polarization variation exists
    - SNR: signal-to-noise ratio from per-channel statistics
    - Effective dynamic range

    Args:
        I_channels: (4, H, W) float32 cleaned polarization [I0, I45, I90, I135]

    Returns:
        float in [0, 1], higher = better quality
    """
    I0 = I_channels[0].astype(np.float64)
    I45 = I_channels[1].astype(np.float64)
    I90 = I_channels[2].astype(np.float64)
    I135 = I_channels[3].astype(np.float64)

    # ── DoLP Contrast ──
    S0 = I0 + I90
    S1 = I0 - I90
    S2 = I45 - I135

    eps = 1e-10
    DoLP = np.sqrt(S1**2 + S2**2) / (S0 + eps)
    DoLP = np.clip(DoLP, 0, 1)

    # Contrast: standard deviation of DoLP
    # High contrast means strong, distinct polarization features
    C_raw = float(np.std(DoLP))

    # ── Signal strength ──
    # Mean energy in S0 (total intensity)
    S0_mean = float(np.mean(S0))
    S_max = float(np.max(S0) + eps)

    S_norm = min(S0_mean / S_max, 1.0)

    # ── Noise estimation ──
    # Estimate noise from local variance across the 4 channels
    # A "clean" image has channels that are smooth and self-consistent
    stacked = np.stack([I0, I45, I90, I135], axis=0)
    channel_means = stacked.mean(axis=(1, 2))  # 4 means
    channel_stds = stacked.std(axis=(1, 2))     # 4 stds

    # Inter-channel mean variation (should be small for consistent polarization)
    mean_spread = float(np.std(channel_means)) / (float(np.mean(channel_means)) + eps)
    mean_spread = min(mean_spread, 1.0)

    # Average channel noise (residual variance after reconstruction)
    noise_est = float(np.mean(channel_stds))
    noise_norm = min(noise_est / 0.5, 1.0)  # normalize: 0.5 std → max noise

    # ── Dynamic range ──
    # Effective fraction of the full [0,1] range used
    dyn_range = float(S0.max() - S0.min())
    dyn_norm = min(dyn_range / (S_max + eps), 1.0)

    # ── Weighted Q score ──
    # Weights tuned for microscopy: contrast and signal matter most
    w_c = 0.35   # DoLP contrast
    w_s = 0.30   # Signal strength
    w_d = 0.15   # Dynamic range
    w_n = 0.10   # Noise penalty
    w_m = 0.10   # Mean consistency penalty

    C_norm = min(C_raw / 0.3, 1.0)  # saturate at 0.3 DoLP std

    Q = (w_c * C_norm + w_s * S_norm + w_d * dyn_norm
         - w_n * noise_norm - w_m * mean_spread)

    Q = float(np.clip(Q, 0.0, 1.0))

    return Q


def quality_label(q_score: float) -> str:
    """Map Q score to a human-readable quality label.

    Args:
        q_score: Q score in [0, 1]

    Returns:
        "Good" (q >= 0.7), "Fair" (q >= 0.4), or "Poor" (q < 0.4)
    """
    if q_score >= Q_GOOD:
        return "Good"
    elif q_score >= Q_FAIR:
        return "Fair"
    else:
        return "Poor"
