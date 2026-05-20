"""Database models for Algae Guardian."""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Text, Enum as SAEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class RiskLevel(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class DeviceStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    device_id = Column(String(50), unique=True, nullable=False, index=True)
    location = Column(String(200))
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    status = Column(String(20), default=DeviceStatus.OFFLINE.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), index=True, nullable=False)
    image_path = Column(String(500))
    processed_image_path = Column(String(500))
    total_count = Column(Integer, default=0)
    concentration_per_ul = Column(Float, default=0.0)
    risk_level = Column(String(20), default=RiskLevel.GREEN.value)
    algae_composition = Column(JSON, default=dict)
    processing_time_ms = Column(Float, default=0.0)
    image_quality = Column(String(20), default="good")
    environment_data = Column(JSON, default=dict, nullable=True)
    full_result = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), index=True, nullable=False)
    detection_id = Column(Integer, nullable=True)
    risk_level = Column(String(20), nullable=False)
    alert_type = Column(String(50))  # concentration_spike, toxic_detected, etc.
    message = Column(Text)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
