"""YOLOv8s detection wrapper for 95-class algae detection.

Takes I_enh grayscale image, converts to 3-channel, runs YOLO inference,
and returns structured detection results with risk levels.
"""
import os
import numpy as np

try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    YOLO = None  # type: ignore
    HAS_ULTRALYTICS = False

from .config import (
    DEFAULT_CONFIDENCE,
    DEFAULT_IOU,
    DEFAULT_IMAGE_SIZE,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    get_class_name,
    get_class_name_zh,
    get_risk_level,
)


def load_yolo(weights_path: str, device: str = "cpu") -> "YOLO":
    """Load YOLOv8s model from weights file.

    Args:
        weights_path: Path to best.pt checkpoint file
        device: 'cpu' or 'cuda' (or 'cuda:0', etc.)

    Returns:
        Ultralytics YOLO model instance

    Raises:
        ImportError: If ultralytics is not installed
        FileNotFoundError: If weights file does not exist
    """
    if not HAS_ULTRALYTICS:
        raise ImportError(
            "ultralytics is required for YOLO detection. "
            "Install with: pip install ultralytics"
        )

    import os
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"YOLO weights not found: {weights_path}")

    model = YOLO(weights_path)
    model.to(device)
    return model


def detect(model: "YOLO",
           I_enh: np.ndarray,
           conf: float = DEFAULT_CONFIDENCE,
           iou: float = DEFAULT_IOU) -> list:
    """Run YOLO detection on enhanced grayscale image.

    Args:
        model: Loaded YOLO model instance
        I_enh: (H, W) float32 or uint8 enhanced grayscale image
        conf: Confidence threshold, default 0.25
        iou: NMS IoU threshold, default 0.7

    Returns:
        list of dicts, each with keys:
            class_id: int
            class_name: str (from LifeWatch 95-class mapping)
            confidence: float
            bbox: [x1, y1, x2, y2] in pixel coordinates
            risk_level: "high" / "medium" / "low"
        Returns empty list if no detections or model has no results.
    """
    if not HAS_ULTRALYTICS:
        raise ImportError("ultralytics is required for YOLO detection.")

    # Convert grayscale to 3-channel RGB for YOLO input
    if I_enh.dtype == np.float32 or I_enh.dtype == np.float64:
        # Scale [0, 1] float to [0, 255] uint8
        I_uint8 = np.clip(I_enh * 255.0, 0, 255).astype(np.uint8)
    else:
        I_uint8 = I_enh.astype(np.uint8)

    # Stack to 3-channel
    if I_uint8.ndim == 2:
        I_3ch = np.stack([I_uint8, I_uint8, I_uint8], axis=-1)
    else:
        I_3ch = I_uint8

    h, w = I_enh.shape[:2]
    imgsz = max(w, h)
    imgsz = max(320, min(imgsz, 1280))

    results = model.predict(
        source=I_3ch,
        conf=conf,
        iou=iou,
        device=model.device if hasattr(model, 'device') else 'cpu',
        imgsz=imgsz,
        verbose=False,
    )

    detections = []
    if not results or len(results) == 0:
        return detections

    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return detections

    for i in range(len(boxes)):
        cls_id = int(boxes.cls[i].item())
        confidence = float(boxes.conf[i].item())
        xyxy = boxes.xyxy[i].tolist()

        # Clamp bbox to image bounds
        x1 = max(0.0, float(xyxy[0]))
        y1 = max(0.0, float(xyxy[1]))
        x2 = min(float(w), float(xyxy[2]))
        y2 = min(float(h), float(xyxy[3]))

        class_name = get_class_name(cls_id)
        class_name_zh = get_class_name_zh(class_name)
        risk_level = get_risk_level(class_name)

        detections.append({
            "class_id": cls_id,
            "class_name": class_name,
            "class_name_zh": class_name_zh,
            "confidence": confidence,
            "bbox": [x1, y1, x2, y2],
            "risk_level": risk_level,
        })

    # Sort by confidence descending
    detections.sort(key=lambda d: d["confidence"], reverse=True)

    return detections


# ── Model switching (V2) ────────────────────────────────────────────────

def load_yolo_by_key(model_key: str = DEFAULT_MODEL, device: str = "cpu") -> "YOLO":
    """Load YOLO model by key from AVAILABLE_MODELS config.

    Resolves weights path relative to algae_image_v2/ root.
    """
    if model_key not in AVAILABLE_MODELS:
        raise ValueError(
            f"Unknown model '{model_key}'. Available: {list(AVAILABLE_MODELS.keys())}"
        )
    cfg = AVAILABLE_MODELS[model_key]
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_path = os.path.join(base_dir, cfg["weights"])
    return load_yolo(weights_path, device)


def get_available_models() -> dict:
    """Return available model configs for API/frontend consumption."""
    return AVAILABLE_MODELS
