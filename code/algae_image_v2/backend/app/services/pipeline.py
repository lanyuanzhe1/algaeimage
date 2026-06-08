"""Pipeline orchestrator — V2 HSV: polarize → (skip RDN) → enhance → YOLO detect."""
import base64
import time
import cv2
import numpy as np

from core_engine.polarization_sim import simulate_polarization
from core_engine.enhancement import enhance, compute_stokes
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

    def run_with_visualization(self, image_path: str) -> dict:
        """Execute V2 pipeline and return every intermediate step as base64 images.

        Pipeline: RGB → HSV polarization → Stokes params → I_enh v2 → YOLO

        Returns dict with:
            steps: list of {title, image (base64 data-URI), description}
            detections, q_score, processing_time_ms, model
        """
        t0 = time.time()

        rgb = cv2.imread(image_path)
        if rgb is None:
            raise ValueError(f"Cannot read image: {image_path}")
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

        def _rgb_to_b64(img_rgb: np.ndarray) -> str:
            """Convert RGB ndarray to base64 data-URI PNG."""
            _, buf = cv2.imencode(".png", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            return "data:image/png;base64," + base64.b64encode(buf).decode()

        def _gray_to_b64(img_gray: np.ndarray) -> str:
            """Convert grayscale ndarray [0,1] to base64 data-URI PNG."""
            vis = np.clip(img_gray * 255, 0, 255).astype(np.uint8)
            _, buf = cv2.imencode(".png", vis)
            return "data:image/png;base64," + base64.b64encode(buf).decode()

        h, w = rgb.shape[:2]

        # Step 1: HSV polarization simulation → 4-channel
        I_channels = simulate_polarization(rgb)

        # Build polarization montage: tile I0, I45, I90, I135
        pol_montage = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
        angle_labels = ["I0 (0°)", "I45 (45°)", "I90 (90°)", "I135 (135°)"]
        for idx in range(4):
            row, col = idx // 2, idx % 2
            ch = np.clip(I_channels[idx] * 255, 0, 255).astype(np.uint8)
            ch_rgb = cv2.cvtColor(ch, cv2.COLOR_GRAY2RGB)
            cv2.putText(ch_rgb, angle_labels[idx], (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            pol_montage[row*h:(row+1)*h, col*w:(col+1)*w] = ch_rgb

        # Step 2: Stokes parameters (DoLP + AoP as color-mapped images)
        stokes = compute_stokes(I_channels)
        DoLP = stokes["DoLP"]
        AoP = stokes["AoP"]

        # DoLP as heatmap
        DoLP_vis = np.clip(DoLP * 255, 0, 255).astype(np.uint8)
        DoLP_rgb = cv2.applyColorMap(DoLP_vis, cv2.COLORMAP_MAGMA)
        cv2.putText(DoLP_rgb, "DoLP", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # AoP as HSV colormap
        AoP_norm = ((AoP + np.pi / 2) / np.pi * 180).astype(np.uint8)
        AoP_hsv = np.zeros((h, w, 3), dtype=np.uint8)
        AoP_hsv[:, :, 0] = AoP_norm
        AoP_hsv[:, :, 1] = 200
        AoP_hsv[:, :, 2] = np.clip(DoLP * 255, 50, 255).astype(np.uint8)
        AoP_rgb = cv2.cvtColor(AoP_hsv, cv2.COLOR_HSV2RGB)
        cv2.putText(AoP_rgb, "AoP", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Stokes montage: DoLP left, AoP right
        stokes_montage = np.hstack([DoLP_rgb, AoP_rgb])

        # Step 3: I_enh v2 enhancement
        I_enh = enhance(I_channels, alpha=IENH_ALPHA, beta=IENH_BETA, gamma=IENH_GAMMA)

        # Step 4: YOLO detection
        detections = detect(self.yolo, I_enh)

        # Step 5: Draw boxes
        result_img = self._draw_boxes(rgb, detections)

        q_score = compute_q_score(I_channels)
        elapsed_ms = (time.time() - t0) * 1000

        return {
            "steps": [
                {
                    "title": "1. RGB原图",
                    "image": _rgb_to_b64(rgb),
                    "description": f"明场显微图像 ({w}×{h})",
                },
                {
                    "title": "2. 偏振模拟",
                    "image": _rgb_to_b64(pol_montage),
                    "description": "HSV色彩空间法 → I0/I45/I90/I135 四通道",
                },
                {
                    "title": "3. Stokes参数",
                    "image": _rgb_to_b64(stokes_montage),
                    "description": "DoLP偏振度 + AoP偏振角 伪彩色图",
                },
                {
                    "title": "4. I_enh v2增强",
                    "image": _gray_to_b64(I_enh),
                    "description": "S0(1+α-γ·DoLP+β·|sin(2·AoP)|·DoLP)",
                },
                {
                    "title": "5. YOLO检测",
                    "image": _rgb_to_b64(result_img),
                    "description": f"{len(detections)} 个检测 · 风险分级标注",
                },
            ],
            "detections": detections,
            "q_score": float(q_score),
            "processing_time_ms": elapsed_ms,
            "model": self.model_key,
        }
