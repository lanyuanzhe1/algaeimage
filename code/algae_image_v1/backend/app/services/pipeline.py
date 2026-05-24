"""Pipeline orchestrator: polarize -> RDN reconstruct -> I_enh enhance -> YOLO detect."""
import time
import cv2
import numpy as np

from core_engine.polarization_sim import simulate_polarization
from core_engine.reconstructor import reconstruct
from core_engine.enhancement import enhance
from core_engine.inference import detect
from core_engine.quality import compute_q_score
from core_engine.config import get_risk_color


class PipelineRunner:
    """Holds pre-loaded RDN and YOLO models. Runs the full detection pipeline."""

    def __init__(self, rdn_model, yolo_model, device: str = "cpu"):
        self.rdn = rdn_model
        self.yolo = yolo_model
        self.device = device

    def run(self, image_path: str) -> dict:
        """
        Execute full pipeline on a single RGB micrograph.

        Args:
            image_path: path to an RGB micrograph file.

        Returns:
            dict with keys:
                detections        — list[dict] from YOLO
                q_score           — float in [0, 1]
                result_image      — np.ndarray (H, W, 3) RGB with boxes drawn
                processing_time_ms — float
        """
        t0 = time.time()

        # 1. Load RGB image
        rgb = cv2.imread(image_path)
        if rgb is None:
            raise ValueError(f"Cannot read image: {image_path}")
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        # 2. Structure-tensor polarization simulation
        I_channels = simulate_polarization(rgb)

        # 3. RDN reconstruction (4ch noisy -> 4ch clean)
        I_clean = reconstruct(self.rdn, I_channels, device=self.device)

        # 4. I_enh v2 de-scattering enhancement
        I_enh = enhance(I_clean)

        # 5. YOLO detection
        detections = detect(self.yolo, I_enh)

        # 6. Q quality score
        q_score = compute_q_score(I_clean)

        # 7. Draw detection boxes on original RGB
        result_img = self._draw_boxes(rgb, detections)

        elapsed_ms = (time.time() - t0) * 1000

        return {
            "detections": detections,
            "q_score": float(q_score),
            "result_image": result_img,
            "processing_time_ms": elapsed_ms,
        }

    def _draw_boxes(self, rgb: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Draw YOLO detection boxes and labels onto the RGB image."""
        img = rgb.copy()
        for d in detections:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            color_hex = get_risk_color(d.get("risk_level", "low"))
            # Hex -> BGR (OpenCV order)
            r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
            color_bgr = (b, g, r)
            cv2.rectangle(img, (x1, y1), (x2, y2), color_bgr, 2)
            label = f"{d['class_name']} {d['confidence']:.2f}"
            cv2.putText(img, label, (x1, max(y1 - 5, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 1)
        return img
