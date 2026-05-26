"""RDN (Residual Dense Network) for polarization image reconstruction.

Architecture: 4ch input -> 16 feat -> 12 RDB blocks x 6 dense layers -> 4ch output.
Total parameters: ~0.6M, model size: ~2.5MB.

Trained on FMPD dataset (293 FlowCam micrographs), PSNR 62.46dB @ epoch 97.
"""
import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    nn = None     # type: ignore
    HAS_TORCH = False


# ── RDN Building Blocks (only if PyTorch available) ───────────────────────

if HAS_TORCH:

    class DenseLayer(nn.Module):
        """Single dense layer for RDB: concat input with conv output."""
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
            self.relu = nn.ReLU(inplace=True)

        def forward(self, x):
            return torch.cat([x, self.relu(self.conv(x))], 1)


    class RDB(nn.Module):
        """Residual Dense Block: N dense layers + local feature fusion."""
        def __init__(self, in_channels: int, growth_rate: int, num_layers: int):
            super().__init__()
            self.layers = nn.Sequential(*[
                DenseLayer(in_channels + growth_rate * i, growth_rate)
                for i in range(num_layers)
            ])
            self.lff = nn.Conv2d(in_channels + growth_rate * num_layers, growth_rate,
                                 kernel_size=1)

        def forward(self, x):
            return x + self.lff(self.layers(x))


    class RDN(nn.Module):
        """Residual Dense Network for polarization reconstruction.

        4ch -> 16feat -> 12xRDB(6 dense layers each, growth=16) -> 4ch
        """
        def __init__(self, num_channels: int = 4, num_features: int = 16,
                     growth_rate: int = 16, num_blocks: int = 12, num_layers: int = 6):
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

else:
    # Stub classes so type hints don't break at import time
    class RDN:
        pass


# ── Public API ──────────────────────────────────────────────────────────────

def load_rdn_model(weights_path: str, device: str = "cpu") -> "nn.Module":
    """Load RDN model from checkpoint weights.

    Args:
        weights_path: Path to .pth checkpoint file
        device: 'cpu' or 'cuda'

    Returns:
        RDN model in eval mode on the specified device

    Raises:
        ImportError: If PyTorch is not installed
        FileNotFoundError: If weights file does not exist
    """
    if not HAS_TORCH:
        raise ImportError(
            "PyTorch is required for RDN reconstruction. "
            "Install with: pip install torch"
        )

    import os
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"RDN weights not found: {weights_path}")

    # Create model matching training config: 4ch -> 16 feat -> 12 blocks x 6 layers -> 4ch
    model = RDN(num_channels=4, num_features=16,
                growth_rate=16, num_blocks=12, num_layers=6)

    checkpoint = torch.load(weights_path, map_location=device, weights_only=True)
    # Filter to only keys present in the model (training checkpoints may have extras)
    model_keys = set(model.state_dict().keys())
    filtered = {k: v for k, v in checkpoint.items() if k in model_keys}

    if not filtered:
        raise ValueError(
            f"No matching keys found between checkpoint ({len(checkpoint)} keys) "
            f"and model ({len(model_keys)} keys). "
            "Check that the weights file is a valid RDN checkpoint."
        )

    model.load_state_dict(filtered, strict=False)
    model.to(device)
    model.eval()

    return model


def reconstruct(model: "nn.Module", I_channels: np.ndarray,
                device: str = "cpu") -> np.ndarray:
    """Run RDN reconstruction on 4-channel polarization input.

    Args:
        model: Loaded RDN model in eval mode
        I_channels: (4, H, W) float32 noisy polarization [I0, I45, I90, I135]
        device: 'cpu' or 'cuda'

    Returns:
        (4, H, W) float32 denoised polarization, same order as input
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch is required for RDN reconstruction.")

    # Normalize input to [0, 1] per-channel
    I_norm = np.zeros_like(I_channels, dtype=np.float32)
    for c in range(4):
        ch = I_channels[c]
        ch_min, ch_max = ch.min(), ch.max()
        if ch_max - ch_min > 1e-10:
            I_norm[c] = (ch - ch_min) / (ch_max - ch_min)

    # Convert to tensor: (1, 4, H, W)
    tensor = torch.from_numpy(I_norm).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(tensor)

    # Back to numpy: (4, H, W) float32
    result = output.squeeze(0).cpu().numpy().astype(np.float32)

    # Clip to valid range
    result = np.clip(result, 0.0, 1.0)

    return result
