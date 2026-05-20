"""YOLOv8 inference wrapper for algae detection."""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np
from ultralytics import YOLO
import cv2

from .config import YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, YOLO_IOU_THRESHOLD
from .config import YOLO_DEVICE, YOLO_IMG_SIZE, ALGAE_CLASSES
from .postprocessing import DetectionResult, parse_yolo_results

logger = logging.getLogger(__name__)


class AlgaeDetector:
    """YOLOv8-based algae detector with full inference pipeline."""

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.model_path = model_path or YOLO_MODEL_PATH
        self.device = device or YOLO_DEVICE
        self.model = None
        self._loaded = False

    def load_model(self) -> bool:
        """Load YOLOv8 model from path. Creates a placeholder if none exists."""
        model_file = Path(self.model_path)
        if not model_file.exists():
            logger.warning(f"Model not found at {self.model_path}, creating placeholder")
            self._create_placeholder_model()

        try:
            self.model = YOLO(self.model_path)
            self._loaded = True
            logger.info(f"YOLOv8 model loaded from {self.model_path} on {self.device}")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False

    def _create_placeholder_model(self):
        """Download a pretrained YOLOv8n model as placeholder for development."""
        from ultralytics import YOLO as YOLODownload
        placeholder = YOLODownload("yolov8n.pt")
        placeholder.save(self.model_path)
        logger.info(f"Saved placeholder YOLOv8n model to {self.model_path}")

    def detect(self, image: np.ndarray, conf: Optional[float] = None,
               iou: Optional[float] = None) -> List[DetectionResult]:
        """Run detection on a single image.

        Args:
            image: RGB image array (H, W, 3)
            conf: confidence threshold override
            iou: NMS IoU threshold override

        Returns:
            List of DetectionResult objects
        """
        if not self._loaded:
            success = self.load_model()
            if not success:
                return []

        conf = conf or YOLO_CONFIDENCE_THRESHOLD
        iou = iou or YOLO_IOU_THRESHOLD

        results = self.model.predict(
            source=image,
            conf=conf,
            iou=iou,
            device=self.device,
            imgsz=YOLO_IMG_SIZE,
            verbose=False,
        )

        return parse_yolo_results(results, ALGAE_CLASSES, image.shape)

    def detect_batch(self, images: List[np.ndarray], **kwargs) -> List[List[DetectionResult]]:
        """Run detection on a batch of images."""
        return [self.detect(img, **kwargs) for img in images]

    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        if not self.model:
            return {"loaded": False}
        return {
            "loaded": True,
            "model_path": self.model_path,
            "device": self.device,
            "num_classes": len(self.model.names) if hasattr(self.model, 'names') else 0,
            "class_names": self.model.names if hasattr(self.model, 'names') else {},
        }
