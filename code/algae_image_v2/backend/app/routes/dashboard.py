"""Dashboard statistics API."""
import json
from fastapi import APIRouter, Depends
import aiosqlite
from ..database import get_db
from ..schemas import StatsResponse

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/stats", response_model=StatsResponse)
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    """Return aggregate detection statistics for the dashboard."""
    # Total count
    row = await db.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
    total = row[0]["c"] if row else 0

    # Today's count
    row = await db.execute_fetchall(
        "SELECT COUNT(*) as c FROM detection_history WHERE date(created_at) = date('now')"
    )
    today = row[0]["c"] if row else 0

    # Class and risk distribution — scan recent detection JSONs
    rows = await db.execute_fetchall(
        "SELECT detections FROM detection_history ORDER BY created_at DESC LIMIT 500"
    )
    class_dist: dict[str, int] = {}
    risk_dist: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        try:
            dets = json.loads(r["detections"])
            for d in dets:
                name = d.get("class_name", "Unknown")
                class_dist[name] = class_dist.get(name, 0) + 1
                risk = d.get("risk_level", "low")
                risk_dist[risk] = risk_dist.get(risk, 0) + 1
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Recent 10 records
    recent = await db.execute_fetchall(
        "SELECT id, filename, risk_level, q_score, created_at "
        "FROM detection_history ORDER BY created_at DESC LIMIT 10"
    )
    recent_list = [
        {
            "id": r["id"],
            "filename": r["filename"],
            "risk_level": r["risk_level"],
            "q_score": r["q_score"],
            "created_at": str(r["created_at"]),
        }
        for r in recent
    ]

    return StatsResponse(
        total_detections=total,
        today_count=today,
        class_distribution=class_dist,
        risk_distribution=risk_dist,
        recent_detections=recent_list,
    )
