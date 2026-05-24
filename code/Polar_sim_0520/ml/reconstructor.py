"""Polarization image reconstruction using RDN / deep learning.

Integrates the Residual Dense Network (RDN) from SPDRDN for reconstructing
high-quality polarization images from raw DoFP inputs, with an analytical
fallback when no trained model is available.

The reconstruction pipeline follows the proposal:
    raw DoFP -> demosaic -> Stokes (S0, S1, S2, DoLP, AoP)
    -> RDN reconstruction (3-channel) -> enhanced output
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# Attempt to import torch (optional dependency)
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("PyTorch not available; polarization reconstruction will use analytical fallback")


class DenseLayer(nn.Module):
    """Single dense layer for RDB."""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return torch.cat([x, self.relu(self.conv(x))], 1)


class RDB(nn.Module):
    """Residual Dense Block."""
    def __init__(self, in_channels: int, growth_rate: int, num_layers: int):
        super().__init__()
        self.layers = nn.Sequential(*[
            DenseLayer(in_channels + growth_rate * i, growth_rate)
            for i in range(num_layers)
        ])
        self.lff = nn.Conv2d(in_channels + growth_rate * num_layers, growth_rate, kernel_size=1)

    def forward(self, x):
        return x + self.lff(self.layers(x))


class RDN(nn.Module):
    """Residual Dense Network for polarization image reconstruction.

    Architecture matches the SPDRDN implementation used in research.
    """
    def __init__(self, num_channels: int = 3, num_features: int = 64,
                 growth_rate: int = 64, num_blocks: int = 4, num_layers: int = 4):
        super().__init__()
        self.G0 = num_features
        self.G = growth_rate
        self.D = num_blocks
        self.C = num_layers

        # Shallow feature extraction
        self.sfe1 = nn.Conv2d(num_channels, num_features, kernel_size=3, padding=1)
        self.sfe2 = nn.Conv2d(num_features, num_features, kernel_size=3, padding=1)

        # Residual dense blocks
        self.rdbs = nn.ModuleList([RDB(self.G0, self.G, self.C)])
        for _ in range(self.D - 1):
            self.rdbs.append(RDB(self.G, self.G, self.C))

        # Global feature fusion
        self.gff = nn.Sequential(
            nn.Conv2d(self.G * self.D, self.G0, kernel_size=1),
            nn.Conv2d(self.G0, self.G0, kernel_size=3, padding=1),
        )

        self.output = nn.Conv2d(self.G0, num_channels, kernel_size=3, padding=1)

    def forward(self, x):
        sfe1 = self.sfe1(x)
        sfe2 = self.sfe2(sfe1)
        x = sfe2

        local_features = []
        for i in range(self.D):
            x = self.rdbs[i](x)
            local_features.append(x)

        x = self.gff(torch.cat(local_features, 1)) + sfe1
        x = self.output(x)
        return x


class PolarizationReconstructor:
    """Polarization image reconstruction using RDN with analytical fallback.

    Supports:
    - RDN-based reconstruction (requires PyTorch and trained weights)
    - Analytical reconstruction using Stokes parameters as fallback
    """

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self.model = None
        self._loaded = False

    def load_model(self) -> bool:
        """Load trained RDN model weights."""
        if not HAS_TORCH:
            logger.warning("PyTorch not available, using analytical reconstruction")
            return False

        if not self.model_path or not Path(self.model_path).exists():
            logger.warning(f"RDN model not found at {self.model_path}, using analytical fallback")
            return False

        try:
            self.model = RDN(num_channels=4, num_features=16,
                             growth_rate=16, num_blocks=12, num_layers=6)
            state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
            # Remove unexpected keys (from training with extra RDBs)
            model_keys = set(self.model.state_dict().keys())
            filtered = {k: v for k, v in state_dict.items() if k in model_keys}
            self.model.load_state_dict(filtered, strict=False)
            self.model.to(self.device)
            self.model.eval()
            self._loaded = True
            logger.info(f"RDN model loaded from {self.model_path} ({len(filtered)}/{len(state_dict)} keys)")
            return True
        except Exception as e:
            logger.error(f"Failed to load RDN model: {e}")
            return False

    def reconstruct_analytical(self, S0: np.ndarray, S1: np.ndarray,
                                S2: np.ndarray) -> np.ndarray:
        """Analytical reconstruction from Stokes parameters (fallback).

        Constructs a 3-channel output:
        - Ch0: S0 normalized (total intensity)
        - Ch1: |S1| normalized (0°/90° difference - horizontal features)
        - Ch2: |S2| normalized (45°/135° difference - diagonal features)

        This preserves polarization contrast information for algae detection.
        """
        def norm(x):
            x_min, x_max = x.min(), x.max()
            if x_max - x_min < 1e-10:
                return np.zeros_like(x, dtype=np.float32)
            return ((x.astype(np.float32) - x_min) / (x_max - x_min) * 255).astype(np.uint8)

        ch0 = norm(S0)
        ch1 = norm(np.abs(S1))
        ch2 = norm(np.abs(S2))

        return np.stack([ch0, ch1, ch2], axis=-1)

    def reconstruct_deep(self, input_tensor: np.ndarray) -> np.ndarray:
        """RDN-based reconstruction: 4ch → 4ch (I0, I45, I90, I135)."""
        if not self._loaded or self.model is None:
            logger.warning("RDN model not loaded, falling back to analytical")
            return self.reconstruct_analytical(
                input_tensor[:, :, 0], input_tensor[:, :, 1], input_tensor[:, :, 2]
            )

        tensor = torch.from_numpy(input_tensor).float().permute(2, 0, 1).unsqueeze(0)
        tensor = tensor.to(self.device)

        with torch.no_grad():
            output = self.model(tensor)

        output = output.squeeze(0).permute(1, 2, 0).cpu().numpy()

        # Normalize each channel to uint8
        out = np.zeros_like(output, dtype=np.uint8)
        for c in range(output.shape[2]):
            ch = output[:, :, c]
            ch = (ch - ch.min()) / (ch.max() - ch.min() + 1e-10) * 255
            out[:, :, c] = ch.astype(np.uint8)

        return out

    def reconstruct(self, ch0: np.ndarray, ch1: np.ndarray,
                    ch2: np.ndarray, ch3: np.ndarray = None,
                    use_deep: bool = True) -> np.ndarray:
        """Reconstruct enhanced polarization image.

        For analytical mode: takes S0, S1, S2 -> 3-channel output.
        For deep mode: takes 4 channels (I0, I45, I90, I135) -> 3-channel output.

        Args:
            ch0, ch1, ch2: First three channels (S0, S1, S2 or I0, I45, I90)
            ch3: Fourth channel (I135), required for deep mode
            use_deep: Use RDN model if available

        Returns:
            (H, W, 3) uint8 reconstruction
        """
        if use_deep and self._loaded and ch3 is not None:
            input_tensor = self._prepare_tensor_4ch(ch0, ch1, ch2, ch3)
            return self.reconstruct_deep(input_tensor)
        return self.reconstruct_analytical(ch0, ch1, ch2)

    def _prepare_tensor(self, S0: np.ndarray, S1: np.ndarray,
                        S2: np.ndarray) -> np.ndarray:
        """Normalize Stokes components to [0, 1] as 3-channel input."""
        def norm(x):
            x_min, x_max = x.min(), x.max()
            if x_max - x_min < 1e-10:
                return np.zeros_like(x, dtype=np.float32)
            return (x.astype(np.float32) - x_min) / (x_max - x_min)

        return np.stack([norm(S0), norm(np.abs(S1)), norm(np.abs(S2))], axis=-1)

    def _prepare_tensor_4ch(self, I0: np.ndarray, I45: np.ndarray,
                             I90: np.ndarray, I135: np.ndarray) -> np.ndarray:
        """Normalize 4 polarization channels to [0, 1] for RDN model input."""
        def norm(x):
            x_min, x_max = x.min(), x.max()
            if x_max - x_min < 1e-10:
                return np.zeros_like(x, dtype=np.float32)
            return (x.astype(np.float32) - x_min) / (x_max - x_min)

        return np.stack([norm(I0), norm(I45), norm(I90), norm(I135)], axis=-1)

    def is_available(self) -> bool:
        """Check if deep reconstruction is available."""
        return self._loaded and HAS_TORCH
