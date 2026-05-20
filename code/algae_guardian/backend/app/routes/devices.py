"""Device management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from ..database import get_async_session
from ..models import Device, DetectionRecord, AlertRecord
from ..schemas import DeviceCreate, DeviceResponse

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])


@router.post("", response_model=DeviceResponse, status_code=201)
async def register_device(device: DeviceCreate, db: AsyncSession = Depends(get_async_session)):
    """Register a new monitoring device."""
    # Check for duplicate device_id
    existing = await db.execute(select(Device).where(Device.device_id == device.device_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Device '{device.device_id}' already exists")

    new_device = Device(**device.model_dump())
    db.add(new_device)
    await db.commit()
    await db.refresh(new_device)
    return DeviceResponse.model_validate(new_device)


@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_async_session)):
    """List all registered devices."""
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    devices = result.scalars().all()
    return [DeviceResponse.model_validate(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: AsyncSession = Depends(get_async_session)):
    """Get device details."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, f"Device '{device_id}' not found")
    return DeviceResponse.model_validate(device)
