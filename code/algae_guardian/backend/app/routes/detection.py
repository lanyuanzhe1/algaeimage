"""Detection API endpoints."""
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List

from ..database import get_async_session
from ..models import DetectionRecord, AlertRecord, Device
from ..schemas import DetectionResponse, DetectionItem
from ..services.detection_service import DetectionService

router = APIRouter(prefix="/api/v1/detection", tags=["Detection"])
detection_service = DetectionService()


@router.post("/upload")
async def upload_and_detect(
    file: UploadFile = File(..., description="Microscopy image (JPEG/PNG)"),
    device_id: str = Form(default="default", description="Source device ID"),
    temperature: Optional[float] = Form(None, description="Water temperature °C"),
    salinity: Optional[float] = Form(None, description="Salinity psu"),
    ph_value: Optional[float] = Form(None, alias="ph", description="pH value"),
    dissolved_oxygen: Optional[float] = Form(None, description="Dissolved oxygen mg/L"),
    db: AsyncSession = Depends(get_async_session),
):
    """Upload an underwater microscopy image and run the full detection pipeline."""
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(400, "Only JPEG/PNG images supported")

    # Read image bytes
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file")

    # Build environment dict
    env = {}
    if temperature is not None:
        env["temperature"] = temperature
    if salinity is not None:
        env["salinity"] = salinity
    if ph_value is not None:
        env["ph"] = ph_value
    if dissolved_oxygen is not None:
        env["dissolved_oxygen"] = dissolved_oxygen

    # Run detection
    try:
        result = detection_service.process_image(image_bytes, device_id, env or None)
    except Exception as e:
        raise HTTPException(500, f"Detection failed: {str(e)}")

    # Save to database
    record = detection_service.create_record(
        db, result, device_id,
        image_path=f"results/{result.image_id}_original.jpg",
        processed_image_path=f"results/{result.image_id}_processed.jpg",
        environment=env or None,
    )

    # Build response
    return DetectionResponse(
        id=record.id,
        device_id=device_id,
        total_count=result.total_count,
        concentration_per_ul=result.concentration_cells_per_ul or 0,
        risk_level=result.risk_level,
        algae_composition=result.algae_composition,
        processing_time_ms=result.processing_time_ms,
        detections=[
            DetectionItem(
                class_id=d.class_id,
                class_name=d.class_name,
                label=d.label,
                confidence=d.confidence,
                bbox=d.bbox,
                risk=d.risk,
                toxicity=d.toxicity,
            ) for d in result.detections
        ],
        image_url=f"/static/results/{result.image_id}_original.jpg",
        processed_image_url=f"/static/results/{result.image_id}_processed.jpg",
        created_at=record.created_at,
    )


@router.get("/history", response_model=List[DetectionResponse])
async def get_detection_history(
    device_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
):
    """Get detection history with optional filters."""
    query = select(DetectionRecord).order_by(desc(DetectionRecord.created_at))

    if device_id:
        query = query.where(DetectionRecord.device_id == device_id)
    if risk_level:
        query = query.where(DetectionRecord.risk_level == risk_level)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return [
        DetectionResponse(
            id=r.id, device_id=r.device_id,
            total_count=r.total_count,
            concentration_per_ul=r.concentration_per_ul,
            risk_level=r.risk_level,
            algae_composition=r.algae_composition or {},
            processing_time_ms=r.processing_time_ms,
            detections=[],
            image_url=f"/static/{r.image_path}" if r.image_path else None,
            processed_image_url=f"/static/{r.processed_image_path}" if r.processed_image_path else None,
            created_at=r.created_at,
        ) for r in records
    ]
