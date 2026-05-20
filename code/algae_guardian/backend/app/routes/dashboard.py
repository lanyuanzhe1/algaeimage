"""Dashboard API endpoints."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..database import get_async_session
from ..models import Device, DetectionRecord, AlertRecord, DeviceStatus
from ..schemas import DashboardSummary, DetectionResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_async_session)):
    """Get dashboard summary statistics."""
    # Device counts
    total_devices = await db.scalar(select(func.count(Device.id)))
    online_devices = await db.scalar(
        select(func.count(Device.id)).where(Device.status == DeviceStatus.ONLINE.value)
    )

    # Today's alerts
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    alerts_today = await db.scalar(
        select(func.count(AlertRecord.id)).where(AlertRecord.created_at >= today_start)
    )

    # Latest detection
    latest_detection = await db.scalar(
        select(DetectionRecord).order_by(desc(DetectionRecord.created_at)).limit(1)
    )
    current_risk = latest_detection.risk_level if latest_detection else "green"

    # Recent detections
    recent_result = await db.execute(
        select(DetectionRecord).order_by(desc(DetectionRecord.created_at)).limit(10)
    )
    recent = recent_result.scalars().all()

    return DashboardSummary(
        total_devices=total_devices or 0,
        online_devices=online_devices or 0,
        alerts_today=alerts_today or 0,
        current_risk_level=current_risk,
        recent_detections=[
            DetectionResponse(
                id=r.id, device_id=r.device_id,
                total_count=r.total_count,
                concentration_per_ul=r.concentration_per_ul,
                risk_level=r.risk_level,
                algae_composition=r.algae_composition or {},
                processing_time_ms=r.processing_time_ms,
                created_at=r.created_at,
            ) for r in recent
        ],
    )
