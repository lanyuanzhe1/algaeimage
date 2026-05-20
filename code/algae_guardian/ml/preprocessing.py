"""Image preprocessing pipeline for algae detection."""
from typing import Optional, Tuple, List
import numpy as np
import cv2


class AlgaePreprocessor:
    """Preprocess images before YOLO inference."""

    def __init__(self, target_size: Tuple[int, int] = (640, 640)):
        self.target_size = target_size

    def resize_with_padding(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Resize image to target size with letterbox padding."""
        h, w = image.shape[:2]
        scale = min(self.target_size[0] / h, self.target_size[1] / w)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        dw = self.target_size[1] - new_w
        dh = self.target_size[0] - new_h

        top, bottom = dh // 2, dh - dh // 2
        left, right = dw // 2, dw - dw // 2

        padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                    cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return padded, scale

    def normalize(self, image: np.ndarray) -> np.ndarray:
        """Normalize image to [0, 1] range."""
        return image.astype(np.float32) / 255.0

    def denoise(self, image: np.ndarray, strength: int = 10) -> np.ndarray:
        """Apply mild denoising while preserving edges."""
        return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE contrast enhancement."""
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)

    def sharpening(self, image: np.ndarray, amount: float = 0.3) -> np.ndarray:
        """Apply unsharp mask."""
        blurred = cv2.GaussianBlur(image, (0, 0), 3)
        sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    def preprocess(self, image: np.ndarray,
                   denoise: bool = True,
                   enhance: bool = True,
                   sharpen: bool = False) -> Tuple[np.ndarray, dict]:
        """Full preprocessing pipeline.

        Args:
            image: Input RGB image (H, W, 3)
            denoise: Apply denoising
            enhance: Apply CLAHE contrast enhancement
            sharpen: Apply sharpening

        Returns:
            Tuple of (preprocessed_image, metadata_dict)
        """
        metadata = {"original_shape": image.shape}

        if denoise:
            image = self.denoise(image)

        if enhance:
            image = self.enhance_contrast(image)

        if sharpen:
            image = self.sharpening(image)

        # Resize for model input
        processed, scale = self.resize_with_padding(image)
        metadata["scale"] = scale
        metadata["padded_shape"] = processed.shape

        # Normalize
        processed = self.normalize(processed)
        metadata["normalized"] = True

        return processed, metadata
