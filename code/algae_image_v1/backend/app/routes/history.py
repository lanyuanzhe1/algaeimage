"""Detection history CRUD API."""
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite
from ..config import UPLOAD_DIR, RESULT_DIR
from ..database import get_db
from ..schemas import HistoryItem, HistoryListResponse

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Paginated list of detection history records."""
    offset = (page - 1) * limit
    rows = await db.execute_fetchall(
        "SELECT id, filename, risk_level, q_score, created_at "
        "FROM detection_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    total_row = await db.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
    total = total_row[0]["c"] if total_row else 0

    items = [
        HistoryItem(
            id=r["id"],
            filename=r["filename"],
            risk_level=r["risk_level"],
            q_score=r["q_score"],
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]
    return HistoryListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/history/{record_id}")
async def get_history_detail(record_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """Return full detail for a single history record, including detection JSON."""
    row = await db.execute_fetchall(
        "SELECT * FROM detection_history WHERE id = ?", (record_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    r = row[0]
    return {
        "id": r["id"],
        "filename": r["filename"],
        "image_path": r["image_path"],
        "result_path": r["result_path"],
        "detections": json.loads(r["detections"]),
        "q_score": r["q_score"],
        "risk_level": r["risk_level"],
        "created_at": str(r["created_at"]),
    }


@router.delete("/history/{record_id}")
async def delete_history(record_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """Delete a history record and its associated uploaded + result files."""
    # Look up file paths before deleting the row
    row = await db.execute_fetchall(
        "SELECT image_path, result_path FROM detection_history WHERE id = ?", (record_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    # Remove stored files if they exist
    image_path = row[0]["image_path"]
    result_path = row[0]["result_path"]
    if image_path and os.path.isfile(image_path):
        os.remove(image_path)
    if result_path:
        # result_path is a URL like /static/results/xxx.png; map back to filesystem
        result_file = os.path.join(RESULT_DIR, os.path.basename(result_path))
        if os.path.isfile(result_file):
            os.remove(result_file)

    await db.execute("DELETE FROM detection_history WHERE id = ?", (record_id,))
    await db.commit()
    return {"status": "deleted", "id": record_id}
