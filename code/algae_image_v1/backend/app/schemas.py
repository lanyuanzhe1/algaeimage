"""Pydantic request/response models for the V1 API."""
from typing import Optional
from pydantic import BaseModel


class DetectionItem(BaseModel):
    """Single detection result from YOLO."""
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]
    risk_level: str     # "high" | "medium" | "low"


class SingleDetectResponse(BaseModel):
    """Response for POST /api/v1/detect."""
    id: str
    filename: str
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    result_image_url: str
    processing_time_ms: float


class BatchResult(BaseModel):
    """Per-image result within a batch response."""
    filename: str
    detections: list[DetectionItem]
    status: str               # "ok" | "error"
    error: Optional[str] = None


class BatchSummary(BaseModel):
    """Aggregated stats across a batch."""
    total_detections: int
    high_risk_count: int
    avg_q_score: float


class BatchDetectResponse(BaseModel):
    """Response for POST /api/v1/detect/batch."""
    batch_id: str
    total: int
    results: list[BatchResult]
    summary: BatchSummary


class StatsResponse(BaseModel):
    """Response for GET /api/v1/dashboard/stats."""
    total_detections: int
    today_count: int
    class_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    recent_detections: list[dict]


class HistoryItem(BaseModel):
    """One row in the history list."""
    id: str
    filename: str
    risk_level: Optional[str]
    q_score: Optional[float]
    created_at: str


class HistoryListResponse(BaseModel):
    """Paginated history response for GET /api/v1/history."""
    items: list[HistoryItem]
    total: int
    page: int
    limit: int
