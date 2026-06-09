"""API routes — detection, dashboard, and history.

Flattened from routes/{detection,dashboard,history}.py into single module.
"""
import json
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
import aiofiles
import aiosqlite
import cv2
import numpy as np

from .config import UPLOAD_DIR, RESULT_DIR
from .database import get_db
from .schemas import (
    BatchDetectResponse,
    BatchResult,
    BatchSummary,
    DetectionItem,
    SingleDetectResponse,
    StatsResponse,
    VizStep,
    VizDetectResponse,
)

router = APIRouter(prefix="/api/v1", tags=["api"])


# ═══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_pipeline():
    """FastAPI dependency: retrieve the global PipelineRunner from app state."""
    from .main import pipeline_runner
    if pipeline_runner is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet — please wait for startup to finish")
    return pipeline_runner


async def _save_upload(file: UploadFile) -> tuple[str, str]:
    """Persist an uploaded file to UPLOAD_DIR.  Returns (file_id, absolute_path)."""
    file_id = uuid.uuid4().hex
    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    safe_name = f"{file_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())
    return file_id, filepath


async def _save_result(file_id: str, result_img) -> str:
    """Write an RGB result image to RESULT_DIR.  Returns the URL path."""
    result_filename = f"{file_id}.png"
    result_path = os.path.join(RESULT_DIR, result_filename)
    cv2.imwrite(result_path, cv2.cvtColor(result_img, cv2.COLOR_RGB2BGR))
    return f"/static/results/{result_filename}"


def _overall_risk(detections: list[dict]) -> Optional[str]:
    """Highest-severity risk level across all detections."""
    risks = [d.get("risk_level", "low") for d in detections]
    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    if risks:
        return "low"
    return None


def _to_detection_items(detections: list[dict]) -> list[DetectionItem]:
    """Convert raw detection dicts to Pydantic DetectionItem list."""
    return [
        DetectionItem(
            class_id=d["class_id"],
            class_name=d["class_name"],
            class_name_zh=d.get("class_name_zh", d["class_name"]),
            confidence=round(d["confidence"], 4),
            bbox=[round(v, 1) for v in d["bbox"]],
            risk_level=d.get("risk_level", "low"),
        )
        for d in detections
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Detection endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/preview")
async def preview_tif(file: UploadFile = File(...)):
    """Convert uploaded image (incl. TIFF) to PNG for browser preview."""
    contents = await file.read()
    arr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Cannot decode image")
    _, png = cv2.imencode(".png", img)
    return Response(content=png.tobytes(), media_type="image/png")


@router.post("/detect", response_model=SingleDetectResponse)
async def detect_single(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
    db: aiosqlite.Connection = Depends(get_db),
    model: str = Query(default="v8l", description="YOLO model key: v8l or v8s"),
):
    """Upload a single micrograph and run the detection pipeline."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, TIF, BMP)")

    file_id, filepath = await _save_upload(file)

    try:
        result = pipeline.run(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    result_url = await _save_result(file_id, result["result_image"])
    det_items = _to_detection_items(result["detections"])
    risk = _overall_risk(result["detections"])

    await db.execute(
        """INSERT INTO detection_history
               (id, filename, image_path, result_path, detections, q_score, risk_level)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            file_id,
            file.filename or "unknown",
            filepath,
            result_url,
            json.dumps([d.model_dump() for d in det_items]),
            round(result["q_score"], 4),
            risk,
        ),
    )
    await db.commit()

    return SingleDetectResponse(
        id=file_id,
        filename=file.filename or "unknown",
        detections=det_items,
        q_score=round(result["q_score"], 4),
        risk_level=risk,
        result_image_url=result_url,
        processing_time_ms=round(result["processing_time_ms"], 1),
    )


@router.post("/detect/batch", response_model=BatchDetectResponse)
async def detect_batch(
    files: list[UploadFile] = File(...),
    pipeline=Depends(get_pipeline),
):
    """Upload up to 50 images and run detection on each."""
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per batch")

    batch_id = uuid.uuid4().hex
    results: list[BatchResult] = []
    total_detections = 0
    high_risk_count = 0
    q_scores: list[float] = []

    for f in files:
        try:
            file_id, filepath = await _save_upload(f)
            result = pipeline.run(filepath)
            await _save_result(file_id, result["result_image"])

            dets = result["detections"]
            total_detections += len(dets)
            risks = [d.get("risk_level", "low") for d in dets]
            if "high" in risks:
                high_risk_count += 1
            q_scores.append(result["q_score"])

            results.append(BatchResult(
                filename=f.filename or "unknown",
                detections=_to_detection_items(dets),
                status="ok",
            ))
        except Exception as e:
            results.append(BatchResult(
                filename=f.filename or "unknown",
                detections=[],
                status="error",
                error=str(e),
            ))

    avg_q = sum(q_scores) / len(q_scores) if q_scores else 0.0

    return BatchDetectResponse(
        batch_id=batch_id,
        total=len(files),
        results=results,
        summary=BatchSummary(
            total_detections=total_detections,
            high_risk_count=high_risk_count,
            avg_q_score=round(avg_q, 4),
        ),
    )


@router.post("/detect/visualize", response_model=VizDetectResponse)
async def detect_visualize(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Upload a single micrograph and run detection WITH intermediate pipeline visualization."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, TIF, BMP)")

    file_id, filepath = await _save_upload(file)

    try:
        result = pipeline.run_with_visualization(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    det_items = _to_detection_items(result["detections"])
    risk = _overall_risk(result["detections"])

    # Decode last step's base64 image back to ndarray for saving
    import base64 as b64
    last_img_b64 = result["steps"][-1]["image"]
    b64_data = last_img_b64.split(",", 1)[1] if "," in last_img_b64 else last_img_b64
    img_bytes = b64.b64decode(b64_data)
    img_arr = np.frombuffer(img_bytes, np.uint8)
    result_rgb = cv2.cvtColor(cv2.imdecode(img_arr, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    result_url = await _save_result(file_id, result_rgb)

    await db.execute(
        """INSERT INTO detection_history
               (id, filename, image_path, result_path, detections, q_score, risk_level)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            file_id,
            file.filename or "unknown",
            filepath,
            result_url,
            json.dumps([d.model_dump() for d in det_items]),
            round(result["q_score"], 4),
            risk,
        ),
    )
    await db.commit()

    return VizDetectResponse(
        id=file_id,
        filename=file.filename or "unknown",
        steps=[VizStep(**s) for s in result["steps"]],
        detections=det_items,
        q_score=round(result["q_score"], 4),
        risk_level=risk,
        processing_time_ms=round(result["processing_time_ms"], 1),
    )

