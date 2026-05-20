"""Post-processing for YOLO detection results."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import numpy as np
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class DetectionResult:
    """Single detection result from YOLO inference."""
    class_id: int
    class_name: str
    label: str               # Chinese name
    confidence: float
    bbox: List[float]        # [x1, y1, x2, y2] normalized
    risk: str                # high / medium / low
    toxicity: bool


@dataclass_json
@dataclass
class BatchResult:
    """Aggregated detection results for one image."""
    image_id: str
    detections: List[DetectionResult] = field(default_factory=list)
    total_count: int = 0
    concentration_cells_per_ul: Optional[float] = None
    algae_composition: Dict[str, int] = field(default_factory=dict)
    risk_level: str = "green"
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_yolo_results(
    results: Any,
    class_defs: Dict[int, Dict[str, Any]],
    image_shape: tuple
) -> List[DetectionResult]:
    """Parse raw YOLO results into structured DetectionResult list."""
    detections = []
    if not results or not results[0].boxes:
        return detections

    h, w = image_shape[:2]
    boxes = results[0].boxes

    for i in range(len(boxes)):
        cls_id = int(boxes.cls[i].item())
        conf = float(boxes.conf[i].item())
        xyxy = boxes.xyxy[i].tolist()

        # Normalize bbox
        norm_bbox = [xyxy[0] / w, xyxy[1] / h, xyxy[2] / w, xyxy[3] / h]

        class_info = class_defs.get(cls_id, {
            "name": f"class_{cls_id}",
            "label": f"未知藻类{cls_id}",
            "risk": "medium",
            "toxicity": False,
        })

        detections.append(DetectionResult(
            class_id=cls_id,
            class_name=class_info["name"],
            label=class_info["label"],
            confidence=conf,
            bbox=norm_bbox,
            risk=class_info["risk"],
            toxicity=class_info["toxicity"],
        ))

    return detections


def count_algae(detections: List[DetectionResult],
                sample_volume_ul: float = 0.001) -> Dict[str, Any]:
    """Count algae detections and estimate concentration.

    Args:
        detections: List of detection results
        sample_volume_ul: Sample volume in μL (default 0.001 for 1mm³ FoV)

    Returns:
        Dict with counts, composition, concentration
    """
    from collections import Counter

    if not detections:
        return {
            "total_count": 0,
            "composition": {},
            "concentration_per_ul": 0.0,
        }

    names = [d.class_name for d in detections]
    composition = dict(Counter(names))

    total = len(detections)
    concentration = total / sample_volume_ul if sample_volume_ul > 0 else 0

    return {
        "total_count": total,
        "composition": composition,
        "concentration_per_ul": round(concentration, 2),
    }


def assess_risk_level(detections: List[DetectionResult],
                      concentration_per_ul: float) -> str:
    """Determine overall risk level based on detections.

    Returns: "green", "yellow", "orange", or "red"
    """
    if not detections:
        return "green"

    has_high_risk = any(d.risk == "high" for d in detections)
    has_toxic = any(d.toxicity for d in detections)
    high_risk_count = sum(1 for d in detections if d.risk == "high")

    # Concentration-based thresholds
    if concentration_per_ul > 500 or (has_high_risk and high_risk_count > 10):
        return "red"
    if concentration_per_ul > 100 or (has_toxic and high_risk_count > 3):
        return "orange"
    if concentration_per_ul > 20 or has_high_risk:
        return "yellow"
    return "green"


def format_results(detections: List[DetectionResult],
                   sample_volume_ul: float = 0.001,
                   image_id: str = "",
                   processing_time_ms: float = 0.0) -> BatchResult:
    """Format detection results into a complete BatchResult."""
    counts = count_algae(detections, sample_volume_ul)
    risk = assess_risk_level(detections, counts["concentration_per_ul"])

    return BatchResult(
        image_id=image_id,
        detections=detections,
        total_count=counts["total_count"],
        concentration_cells_per_ul=counts["concentration_per_ul"],
        algae_composition=counts["composition"],
        risk_level=risk,
        processing_time_ms=processing_time_ms,
    )
