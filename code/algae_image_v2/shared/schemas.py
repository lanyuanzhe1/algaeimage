"""藻影知微 V2 — 共享 Pydantic Schemas（backend + deploy 共用）

单一来源: 任何 API 契约变更只需修改此文件，backend 和 deploy/server_light.py 自动同步。

依赖: pydantic>=2.0（无 torch / cv2 / numpy 依赖）
"""
from typing import Optional
from pydantic import BaseModel


class DetectionItem(BaseModel):
    """单条 YOLO 检测结果"""
    class_id: int
    class_name: str
    class_name_zh: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]
    risk_level: str     # "high" | "medium" | "low"


class SingleDetectResponse(BaseModel):
    """POST /api/v1/detect 响应"""
    id: str
    filename: str
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    result_image_url: str
    processing_time_ms: float


class BatchResult(BaseModel):
    """批量检测中单张结果"""
    filename: str
    detections: list[DetectionItem]
    status: str               # "ok" | "error"
    error: Optional[str] = None


class BatchSummary(BaseModel):
    """批量检测汇总统计"""
    total_detections: int
    high_risk_count: int
    avg_q_score: float


class BatchDetectResponse(BaseModel):
    """POST /api/v1/detect/batch 响应"""
    batch_id: str
    total: int
    results: list[BatchResult]
    summary: BatchSummary


class StatsResponse(BaseModel):
    """GET /api/v1/dashboard/stats 响应"""
    total_detections: int
    today_count: int
    class_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    recent_detections: list[dict]


class HistoryItem(BaseModel):
    """历史记录列表项"""
    id: str
    filename: str
    risk_level: Optional[str]
    q_score: Optional[float]
    created_at: str


class HistoryListResponse(BaseModel):
    """GET /api/v1/history 响应"""
    items: list[HistoryItem]
    total: int
    page: int
    limit: int


class VizStep(BaseModel):
    """管线可视化中间步骤"""
    title: str
    image: str              # data:image/png;base64,...
    description: str


class VizDetectResponse(BaseModel):
    """POST /api/v1/detect/visualize 响应 — 含 5 步管线可视化"""
    id: str
    filename: str
    steps: list[VizStep]
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    processing_time_ms: float


class LatestResult(BaseModel):
    """/detect/latest 返回的单条摘要 (不含 base64 图片，保持轻量)"""
    id: str
    filename: str
    detections: list[DetectionItem]
    q_score: float
    risk_level: Optional[str] = None
    processing_time_ms: float
    raw_image_url: Optional[str] = None       # 原始采集图 URL，手动上传时为 null
    result_image_url: Optional[str] = None    # YOLO 标注图 URL，手动上传时为 null


class LatestResultsResponse(BaseModel):
    """GET /api/v1/detect/latest 响应"""
    results: list[LatestResult]
    count: int


class StreamStatusResponse(BaseModel):
    """GET /api/v1/detect/stream-status 响应"""
    active: bool
    total_frames: int
    buffer_size: int
    elapsed_seconds: float
    effective_fps: float


# ══════════════════════════════════════════════════════════════════
# Device Management
# ══════════════════════════════════════════════════════════════════

class DeviceInfo(BaseModel):
    """单个设备信息"""
    id: str
    name: str
    location: str
    model: str
    status: str  # "online" | "offline"
    today_frames: int
    alerts: int
    uptime: str

class DeviceListResponse(BaseModel):
    """GET /api/v1/devices 响应"""
    devices: list[DeviceInfo]


# ══════════════════════════════════════════════════════════════════
# Review
# ══════════════════════════════════════════════════════════════════

class ReviewItem(BaseModel):
    """单条复核记录"""
    id: str
    detection_id: str
    filename: str
    class_name: str
    class_name_zh: str
    confidence: float
    risk_level: Optional[str] = None
    status: str  # "pending" | "approved" | "rejected"
    created_at: str

class ReviewListResponse(BaseModel):
    """GET /api/v1/review/list 响应"""
    items: list[ReviewItem]
    total: int
    approved_count: int
    pending_count: int

class ReviewSubmitRequest(BaseModel):
    """POST /api/v1/review/submit 请求"""
    detection_id: str
    status: str  # "approved" | "rejected"
    corrected_class: Optional[str] = None
