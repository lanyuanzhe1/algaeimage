"""Image enhancement: underwater color correction, contrast enhancement."""
import numpy as np
import cv2
from typing import Tuple, Optional


class ImageEnhancer:
    """Underwater image enhancement for algae imaging."""

    def __init__(self):
        pass

    def underwater_color_correction(self, image: np.ndarray,
                                    clip_percentile: float = 2.0) -> np.ndarray:
        """Apply histogram-based color correction for underwater images.

        Assumes some color cast due to water absorption (red attenuation).
        """
        result = image.copy().astype(np.float32)

        for c in range(3):
            channel = image[:, :, c]
            low = np.percentile(channel, clip_percentile)
            high = np.percentile(channel, 100 - clip_percentile)
            if high > low:
                result[:, :, c] = np.clip(
                    (channel.astype(np.float32) - low) * 255.0 / (high - low), 0, 255
                )

        return result.astype(np.uint8)

    def adaptive_histogram_equalization(self, image: np.ndarray,
                                        clip_limit: float = 3.0,
                                        grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
        """Apply CLAHE for local contrast enhancement."""
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
        l_eq = clahe.apply(l)
        enhanced = cv2.merge([l_eq, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)

    def dark_channel_prior(self, image: np.ndarray, patch_size: int = 15) -> np.ndarray:
        """Compute dark channel prior for dehazing."""
        h, w = image.shape[:2]
        padded = cv2.copyMakeBorder(image, patch_size // 2, patch_size // 2,
                                    patch_size // 2, patch_size // 2,
                                    cv2.BORDER_REPLICATE)
        dark = np.zeros((h, w))
        for i in range(h):
            for j in range(w):
                patch = padded[i:i + patch_size, j:j + patch_size]
                dark[i, j] = np.min(patch)
        return dark

    def dehaze(self, image: np.ndarray, omega: float = 0.95,
               patch_size: int = 15) -> np.ndarray:
        """Simple dark-channel dehazing for turbid water."""
        img = image.astype(np.float32) / 255.0
        dark = self.dark_channel_prior((img * 255).astype(np.uint8), patch_size) / 255.0

        # Estimate atmospheric light
        flat = dark.flatten()
        num_pixels = int(len(flat) * 0.001)
        indices = np.argpartition(flat, -num_pixels)[-num_pixels:]
        bright_pixels = np.unravel_index(indices, dark.shape)
        atmosphere = np.mean(img[bright_pixels], axis=0)

        # Estimate transmission
        transmission = 1.0 - omega * dark
        transmission = np.clip(transmission, 0.1, 1.0)

        # Recover scene radiance
        result = np.zeros_like(img)
        for c in range(3):
            result[:, :, c] = (img[:, :, c] - atmosphere[c]) / transmission + atmosphere[c]

        return np.clip(result * 255, 0, 255).astype(np.uint8)

    def enhance(self, image: np.ndarray,
                color_correct: bool = True,
                clahe: bool = True,
                dehaze: bool = False) -> np.ndarray:
        """Composite enhancement pipeline."""
        result = image.copy()

        if dehaze:
            result = self.dehaze(result)

        if color_correct:
            result = self.underwater_color_correction(result)

        if clahe:
            result = self.adaptive_histogram_equalization(result)

        return result
