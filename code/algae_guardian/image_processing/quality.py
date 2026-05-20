"""Image quality assessment for algae microscopy images with weighted scoring."""
import numpy as np
import cv2
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass, asdict


@dataclass
class QualityReport:
    sharpness: float           # Laplacian variance (S)
    brightness: float          # Mean intensity
    contrast: float            # Standard deviation (C)
    blur_detected: bool
    overexposed: bool
    underexposed: bool
    overall_quality: str       # good / fair / poor
    issues: list               # List of quality issue descriptions
    quality_score: float = 0.0  # Q score from weighted formula


class QualityAssessor:
    """Assess image quality for algae microscopy images.

    Implements the weighted quality scoring formula:
        Q = w_c * C + w_s * S + w_f * F - w_o * O - w_b * B

    where:
        C = target region contrast (normalized)
        S = sharpness / gradient strength (normalized)
        F = effective FoV ratio
        O = overexposure ratio
        B = bubble / occlusion ratio
    """

    def __init__(self,
                 blur_threshold: float = 100.0,
                 overexposure_threshold: float = 245,
                 underexposure_threshold: float = 10,
                 min_brightness: float = 30,
                 max_brightness: float = 220,
                 # Weighted formula coefficients
                 w_c: float = 0.35,
                 w_s: float = 0.35,
                 w_f: float = 0.15,
                 w_o: float = 0.10,
                 w_b: float = 0.05,
                 # Quality thresholds
                 q_good: float = 0.65,
                 q_fair: float = 0.40):
        self.blur_threshold = blur_threshold
        self.overexposure_threshold = overexposure_threshold
        self.underexposure_threshold = underexposure_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

        # Quality scoring weights
        self.w_c = w_c
        self.w_s = w_s
        self.w_f = w_f
        self.w_o = w_o
        self.w_b = w_b
        self.q_good = q_good
        self.q_fair = q_fair

    def assess(self, image: np.ndarray) -> QualityReport:
        """Run full quality assessment with weighted scoring."""
        issues = []

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        h, w = gray.shape

        # ── Sharpness (S) ──
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_raw = laplacian.var()

        is_blurry = sharpness_raw < self.blur_threshold
        if is_blurry:
            issues.append(f"图像模糊 (sharpness={sharpness_raw:.1f})")

        # ── Contrast (C) ──
        contrast_raw = np.std(gray)

        # ── Brightness / exposure ──
        brightness = np.mean(gray)
        is_overexposed = brightness > self.max_brightness
        is_underexposed = brightness < self.min_brightness

        if is_overexposed:
            issues.append(f"过曝 (brightness={brightness:.1f})")
        if is_underexposed:
            issues.append(f"欠曝 (brightness={brightness:.1f})")

        # ── Overexposure ratio (O) ──
        over_ratio = float(np.mean(gray > self.overexposure_threshold))
        under_ratio = float(np.mean(gray < self.underexposure_threshold))

        # ── Effective FoV ratio (F) ──
        # Estimate usable area: regions with valid intensity range
        valid_mask = (gray > self.underexposure_threshold) & (gray < self.overexposure_threshold)
        effective_fov_ratio = float(np.mean(valid_mask))

        # ── Bubble / occlusion ratio (B) ──
        # Dark circular regions (bubbles) or large uniform patches (occlusion)
        bubble_ratio = self._estimate_bubble_ratio(gray)

        # ── Normalize components to [0, 1] ──
        # Contrast: typical max ~128 for 8-bit
        C_norm = min(contrast_raw / 80.0, 1.0)
        # Sharpness: typical max ~1000 for Laplacian variance
        S_norm = min(sharpness_raw / 500.0, 1.0)
        F_norm = effective_fov_ratio
        O_norm = over_ratio
        B_norm = bubble_ratio

        # ── Weighted quality score Q ──
        Q = (self.w_c * C_norm + self.w_s * S_norm + self.w_f * F_norm
             - self.w_o * O_norm - self.w_b * B_norm)
        Q = float(np.clip(Q, 0.0, 1.0))

        # ── Overall quality from Q ──
        if Q >= self.q_good and not is_blurry:
            overall = "good"
        elif Q >= self.q_fair:
            overall = "fair"
        else:
            overall = "poor"

        return QualityReport(
            sharpness=round(sharpness_raw, 2),
            brightness=round(brightness, 2),
            contrast=round(contrast_raw, 2),
            blur_detected=is_blurry,
            overexposed=is_overexposed,
            underexposed=is_underexposed,
            overall_quality=overall,
            issues=issues,
            quality_score=round(Q, 4),
        )

    def _estimate_bubble_ratio(self, gray: np.ndarray) -> float:
        """Estimate ratio of image occluded by bubbles or debris."""
        # Edge detection to find bubble boundaries
        edges = cv2.Canny(gray, 30, 100)
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Filter for circular-ish contours (bubbles) and large debris
        h, w = gray.shape
        total_area = h * w
        occlusion_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50:  # Too small to matter
                continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            # Bubbles are circular; debris has low circularity
            if circularity > 0.5 or area > 0.05 * total_area:
                occlusion_area += area

        return min(occlusion_area / total_area, 1.0)

    def is_usable(self, report: QualityReport) -> bool:
        """Check if image quality is acceptable for detection."""
        return report.overall_quality != "poor" and report.quality_score >= self.q_fair

    def get_detailed_report(self, image: np.ndarray) -> Dict[str, Any]:
        """Get detailed quality metrics as a dict for logging/debugging."""
        report = self.assess(image)
        result = asdict(report)
        # Add derived metrics
        result["quality_score_pct"] = round(report.quality_score * 100, 1)
        return result
