"""Review workflow API — saves reviewed samples to disk for the data loop."""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..database import get_async_session
from ..models import DetectionRecord

router = APIRouter(prefix="/api/v1/review", tags=["Review"])

# Folder where reviewed samples are stored
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REVIEW_DIR = PROJECT_ROOT / "backend" / "data" / "reviewed"
TRAINING_DIR = PROJECT_ROOT / "backend" / "data" / "training_pool"
for d in [REVIEW_DIR, TRAINING_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class ReviewSubmit(BaseModel):
    site_id: str
    site_name: str
    risk: str
    count: int
    concentration: float
    confidence: float
    species: list  # [{name, count, ratio, confidence, risk}]
    image_src: str = ""  # current microscope image path
    note: str = ""


class ReviewRecord(BaseModel):
    id: str
    site_id: str
    site_name: str
    risk: str
    status: str  # "reviewed" or "training"
    image_path: str
    reviewed_at: str


@router.post("/submit")
async def submit_review(payload: ReviewSubmit):
    """Submit a manual review. Saves snapshot + metadata to reviewed/ folder."""
    review_id = datetime.utcnow().strftime("review_%Y%m%d_%H%M%S_%f")
    review_dir = REVIEW_DIR / review_id
    review_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata JSON
    meta = {
        "id": review_id,
        "site_id": payload.site_id,
        "site_name": payload.site_name,
        "risk": payload.risk,
        "count": payload.count,
        "concentration": payload.concentration,
        "confidence": payload.confidence,
        "species": payload.species,
        "note": payload.note,
        "status": "reviewed",
        "reviewed_at": datetime.utcnow().isoformat(),
    }
    with open(review_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Copy source image if available
    image_path = ""
    if payload.image_src:
        src_path = PROJECT_ROOT / payload.image_src.lstrip("/")
        if src_path.exists():
            dst_path = review_dir / f"{review_id}_image{src_path.suffix}"
            shutil.copy2(src_path, dst_path)
            image_path = str(dst_path)

    return {
        "ok": True,
        "id": review_id,
        "image_path": image_path,
        "message": f"复核记录已保存: {review_id}",
    }


@router.get("/list")
async def list_reviews(status: Optional[str] = None):
    """List reviewed samples from disk."""
    results = []
    for d in sorted(REVIEW_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        meta_file = d / "metadata.json"
        if not meta_file.exists():
            continue
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if status and meta.get("status") != status:
            continue
        # Find image in the review dir
        img = ""
        for f_path in d.iterdir():
            if f_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                img = str(f_path)
                break
        results.append({
            "id": meta["id"],
            "site_id": meta.get("site_id", ""),
            "site_name": meta.get("site_name", ""),
            "risk": meta.get("risk", ""),
            "status": meta.get("status", "reviewed"),
            "image_path": img,
            "reviewed_at": meta.get("reviewed_at", ""),
        })
    return results


@router.post("/approve/{review_id}")
async def approve_for_training(review_id: str):
    """Approve a reviewed sample and move it to the training pool."""
    review_dir = REVIEW_DIR / review_id
    if not review_dir.exists():
        raise HTTPException(404, f"Review {review_id} not found")

    # Update metadata
    meta_file = review_dir / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["status"] = "training"
        meta["approved_at"] = datetime.utcnow().isoformat()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # Copy to training pool
    train_dst = TRAINING_DIR / review_id
    if not train_dst.exists():
        shutil.copytree(review_dir, train_dst)

    return {
        "ok": True,
        "id": review_id,
        "message": f"已加入训练集: {review_id}",
    }


@router.get("/stats")
async def review_stats():
    """Get review statistics."""
    reviewed_count = len([d for d in REVIEW_DIR.iterdir() if d.is_dir() and (d / "metadata.json").exists()])
    training_count = len([d for d in TRAINING_DIR.iterdir() if d.is_dir() and (d / "metadata.json").exists()])
    return {
        "total_reviewed": reviewed_count,
        "total_training": training_count,
        "reviewed_dir": str(REVIEW_DIR),
        "training_dir": str(TRAINING_DIR),
    }
