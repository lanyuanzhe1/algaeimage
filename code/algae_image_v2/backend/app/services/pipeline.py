"""Pipeline orchestrator — V2 HSV: polarize → (skip RDN) → enhance → YOLO detect."""
import time
import cv2
import numpy as np

from core_engine.polarization_sim import simulate_polarization
from core_engine.enhancement import enhance
from core_engine.inference import detect, load_yolo_by_key
from core_engine.quality import compute_q_score
from core_engine.config import get_risk_color, SKIP_RDN, DEFAULT_MODEL, IENH_ALPHA, IENH_BETA, IENH_GAMMA


class PipelineRunner:
    """Holds pre-loaded YOLO model. RDN is optional (skipped by default in V2)."""

    def __init__(self, yolo_model, device: str = "cpu", model_key: str = DEFAULT_MODEL):
        self.yolo = yolo_model
        self.device = device
        self.model_key = model_key

    @classmethod
    def create(cls, model_key: str = DEFAULT_MODEL, device: str = "cpu"):
        """Factory: load YOLO by model key from AVAILABLE_MODELS config."""
        yolo = load_yolo_by_key(model_key, device)
        return cls(yolo, device, model_key)

    def run(self, image_path: str) -> dict:
        """Execute V2 HSV pipeline on a single RGB micrograph.

        Pipeline: RGB → HSV polarization → (RDN skip) → I_enh v2 → YOLO
        """
        t0 = time.time()

        rgb = cv2.imread(image_path)
        if rgb is None:
            raise ValueError(f"Cannot read image: {image_path}")
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        # 1. HSV polarization simulation
        I_channels = simulate_polarization(rgb)

        # 2. (RDN skipped in V2 — HSV is deterministic, no denoising needed)
        I_clean = I_channels  # pass-through

        # 3. I_enh v2 de-scattering enhancement
        I_enh = enhance(I_clean, alpha=IENH_ALPHA, beta=IENH_BETA, gamma=IENH_GAMMA)

        # 4. YOLO detection
        detections = detect(self.yolo, I_enh)

        # 5. Q quality score
        q_score = compute_q_score(I_clean)

        # 6. Draw boxes on original RGB
        result_img = self._draw_boxes(rgb, detections)

        elapsed_ms = (time.time() - t0) * 1000

        return {
            "detections": detections,
            "q_score": float(q_score),
            "result_image": result_img,
            "processing_time_ms": elapsed_ms,
            "model": self.model_key,
        }

    def _draw_boxes(self, rgb: np.ndarray, detections: list[dict]) -> np.ndarray:
        img = rgb.copy()
        for d in detections:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            color_hex = get_risk_color(d.get("risk_level", "low"))
            r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
            color_bgr = (b, g, r)
            cv2.rectangle(img, (x1, y1), (x2, y2), color_bgr, 6)
            label = f"{d['class_name']} {d['confidence']:.2f}"
            cv2.putText(img, label, (x1, max(y1 - 8, 30)),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, color_bgr, 4)
        return img
