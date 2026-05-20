"""API request/response schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── Device Schemas ──

class DeviceCreate(BaseModel):
    name: str = Field(..., description="Device name")
    device_id: str = Field(..., description="Unique device identifier")
    location: Optional[str] = None
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0


class DeviceResponse(BaseModel):
    id: int
    name: str
    device_id: str
    location: Optional[str] = None
    latitude: float = 0.0
    longitude: float = 0.0
    status: str = "offline"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Detection Schemas ──

class DetectionRequest(BaseModel):
    device_id: str = Field(..., description="Source device ID")
    environment: Optional[Dict[str, float]] = Field(
        default=None,
        description="Environment data: temp, salinity, pH, DO, etc."
    )


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionItem(BaseModel):
    class_id: int
    class_name: str
    label: str
    confidence: float
    bbox: List[float]
    risk: str
    toxicity: bool


class DetectionResponse(BaseModel):
    id: int
    device_id: str
    total_count: int
    concentration_per_ul: float
    risk_level: str
    algae_composition: Dict[str, int]
    processing_time_ms: float
    detections: List[DetectionItem] = []
    image_url: Optional[str] = None
    processed_image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DetectionHistoryParams(BaseModel):
    device_id: Optional[str] = None
    risk_level: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ── Alert Schemas ──

class AlertResponse(BaseModel):
    id: int
    device_id: str
    risk_level: str
    alert_type: str
    message: str
    acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard Schemas ──

class DashboardSummary(BaseModel):
    total_devices: int
    online_devices: int
    alerts_today: int
    current_risk_level: str
    recent_detections: List[DetectionResponse] = []
    algae_trend: Dict[str, List[Dict]] = {}


class RiskAssessmentRequest(BaseModel):
    device_id: str
    detections: List[DetectionItem] = []
    environment: Dict[str, float] = {}
